from core_system.users.models.user_model import User
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from shared.helpers.client_creator import ClientCreator
from mock import patch
from pony.orm import db_session
from tests.factories.factories import AbstractUserFactory
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.factories import DeviceAbstractFactory
from payg_loan_system.actions.swap_device import handle_device_change_request
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
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
