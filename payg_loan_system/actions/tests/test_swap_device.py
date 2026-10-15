from datetime import datetime, timedelta
from uuid import uuid4

from core_system.users.models.user_model import User
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from shared.helpers.client_creator import ClientCreator
from mock import patch
from pony.orm import db_session, flush
from tests.factories.factories import AbstractUserFactory
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.factories import DeviceAbstractFactory
from payg_loan_system.actions.swap_device import handle_device_change_request
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIHelperV2
from payg_loan_system.devices.model.offline_token_model import TokenType
from payg_loan_system.devices.model.token import Token
from shared.helpers.assert_datetime import assert_datetime
from payg_loan_system.contracts.services.contract_event_service import ContractEventService


class TestSwapDevice:

    def test_user_without_auth(self, *args):
        user = AbstractUserFactory.create(authorized=False)
        old_device = DeviceAbstractFactory.create()
        new_device = DeviceAbstractFactory.create_no_client()

        resp = handle_device_change_request(user, old_device.contract, new_device)

        assert resp == [{'success': False,
                        'status': 'INSUFFICIENT_PERMISSION',
                        'permission': 'SwapDeviceActions'}]

    @db_session
    def test_new_device_already_registered(self, api_client, good_api_key, super_admin_user, *args):
        user = super_admin_user()
        old_device = ClientCreator.create(api_client, good_api_key).contracts.select().first().linked_device #DeviceAbstractFactory.create()
        new_device = ClientCreator.create(api_client, good_api_key).contracts.select().first().linked_device #DeviceAbstractFactory.create()

        resp = handle_device_change_request(user, old_device.contract, new_device)

        assert resp[0]['status'] == 'DEVICE_ALREADY_REGISTERED'

    @db_session
    def test_new_device_not_allowed_on_offer(self, api_client, good_api_key, super_admin_user, *args):
        user = super_admin_user()
        old_device = ClientCreator.create(api_client, good_api_key).contracts.select().first().linked_device #DeviceAbstractFactory.create()
        new_device = DeviceCreateService.create("ERTERT34534534", 'NPG', 1) #DeviceAbstractFactory.create_no_client()

        with patch.object(Device, 'can_use_offer', return_value=False):
            resp = handle_device_change_request(user, old_device.contract, new_device)

        assert resp == [{'success': False, 'status': 'DEVICE_NOT_ALLOWED_ON_OFFER'}]
        new_device.delete()

    # @patch.object(DeviceAPIService, 'sync_device_settings', return_value='PANCAKES')
    # @patch('payg_loan_system.actions.swap_device.save_mentor_request')
    # @patch.object(ContractEventService, 'create_contract_device_swap_event')
    @db_session
    def test_swap_device_success(self, api_client, good_api_key, super_admin_user, *args):
        user = super_admin_user()
        old_device = ClientCreator.create(api_client, good_api_key).contracts.select().first().linked_device #DeviceAbstractFactory.create()
        new_device = DeviceCreateService.create("ERTET4534", "NPG", 1) #DeviceAbstractFactory.create_no_client()
        client = old_device.contract.client
        contract = old_device.contract

        old_device_client = client
        old_device_activeuntil = old_device.ActiveUntil
        old_device_offer = old_device.contract.offer

        with patch.object(DeviceAPIService, 'sync_device_settings', return_value='PANCAKES'):
            resp = handle_device_change_request(user, contract, new_device)
        
        assert resp[0] == {'success': True,
                           'status': 'DEVICE_CHANGE_SUCCESS_NO_CODE',
                           'client_id': client.id,
                           'name': client.person.name,
                           'surname': client.person.surname,
                           'new_device_serial_number': new_device.get_display_name(),
                           'old_device_serial_number': old_device.get_display_name(),
                           'registration_answer_code_new': 'PANCAKES',
                           'registration_answer_code_old': 'PANCAKES'}
        assert new_device.contract.client == old_device_client
        assert new_device.contract.offer == old_device_offer
        assert new_device.contract == contract
        assert_datetime(new_device.ActiveUntil, old_device_activeuntil)


class TestSwapDeviceZeroDayTokens:
    """
    PVStar report (2026-06-09): an expired device swapped for a brand-new device with no credit
    produced a 0-day ADD_CREDIT token request for both devices, which PVStar rejects
    ("minimum number of days for recharge is 1").
    """

    @staticmethod
    def _expired_contract_device(api_client, good_api_key):
        old_device = ClientCreator.create(api_client, good_api_key).contracts.select().first().linked_device
        old_device.ActiveUntil = datetime.now() - timedelta(days=20)
        flush()
        return old_device

    @staticmethod
    def _swap(user, contract, new_device):
        with patch.object(DeviceAPIHelperV2, 'post_credit_update', return_value='111 222 333') as post_credit_update:
            resp = handle_device_change_request(user, contract, new_device)
        posted = [(call.args[0], call.kwargs['data']) for call in post_credit_update.call_args_list]
        return resp, posted

    @db_session
    def test_expired_device_swapped_for_new_device_without_credit(self, api_client, good_api_key, super_admin_user, *args):
        user = super_admin_user()
        old_device = self._expired_contract_device(api_client, good_api_key)
        contract = old_device.contract
        new_device = DeviceCreateService.create("PVSNEW0001", "1WY", 1)

        resp, posted = self._swap(user, contract, new_device)

        assert resp[0]['success'] is True
        assert resp[0]['status'] == 'DEVICE_CHANGE_SUCCESS_NO_CODE'
        # Old device: credit is reset with an explicit SET to now (0 days), not a 0-day ADD
        old_device_updates = [data for device, data in posted if device == old_device]
        assert len(old_device_updates) == 1
        assert old_device_updates[0]['credit_update_type'] == TokenType.set_credit
        # New device: no token requested, the client is told to pay instead
        assert [data for device, data in posted if device == new_device] == []
        assert resp[-1]['success'] is False
        assert resp[-1]['status'] == 'NO_ACTIVATION_TIME_ON_DEVICE'
        assert resp[-1]['contract_reference'] == contract.reference

    @db_session
    def test_active_device_swapped_for_new_device_transfers_time(self, api_client, good_api_key, super_admin_user, *args):
        user = super_admin_user()
        # 10 days paid on top of the deposit: the contract (and so the new device) has activation time left
        old_device = ClientCreator.create(api_client, good_api_key, extra_paid=10).contracts.select().first().linked_device
        contract = old_device.contract
        new_device = DeviceCreateService.create("PVSNEW0002", "1WY", 1)

        resp, posted = self._swap(user, contract, new_device)

        new_device_updates = [data for device, data in posted if device == new_device]
        assert len(new_device_updates) == 1
        assert new_device_updates[0]['credit_update_type'] == TokenType.add_credit
        assert new_device.ActiveUntil > datetime.now() + timedelta(days=5)
        assert_datetime(new_device_updates[0]['credit_value'], new_device.ActiveUntil)
        assert resp[-1]['success'] is True
        assert resp[-1]['status'] == 'ACTIVATION_REQUEST_SUCCESS'
        assert resp[-1]['activation_answer_code'] == '111 222 333'

    @db_session
    def test_expired_device_swapped_for_previously_used_device_still_syncs(self, api_client, good_api_key, super_admin_user, *args):
        # A previously used device may still hold credit from its last token, so it keeps being forced in sync
        user = super_admin_user()
        old_device = self._expired_contract_device(api_client, good_api_key)
        contract = old_device.contract
        new_device = DeviceCreateService.create("PVSNEW0003", "1WY", 1)
        Token(time=datetime.now() - timedelta(days=60), uuid=str(uuid4()), device=new_device, request_code='',
              token='999 999 999', mode=new_device.Mode, expiration_time=datetime.now() - timedelta(days=30),
              token_type=TokenType.add_credit, credit_unit='ABSOLUTE_TIME')
        flush()

        resp, posted = self._swap(user, contract, new_device)

        assert len([data for device, data in posted if device == new_device]) == 1
        assert resp[-1]['status'] == 'ACTIVATION_REQUEST_SUCCESS'
