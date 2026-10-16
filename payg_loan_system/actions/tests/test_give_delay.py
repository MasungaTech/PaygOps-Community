from mock import patch
from pony.orm import db_session
from shared.helpers.client_creator import ClientCreator
from tests.factories.factories import AbstractUserFactory
from payg_loan_system.devices.factories import DeviceAbstractFactory
from payg_loan_system.actions.give_delay import handle_give_delay_request, ContractRepaymentService

from payg_loan_system.contracts.services.tests.factories import ContractRepaymentFactory
patcher_2 = patch.object(ContractRepaymentService, 'give_days_grace_period', return_value=ContractRepaymentFactory.stub())


class TestGiveDelay:

    @db_session
    def test_user_without_auth(self, api_client, good_api_key,*args):
        user = AbstractUserFactory.create(authorized=False)
        device = ClientCreator.create(api_client, good_api_key).contracts.select().first().linked_device
        client = device.contract.client

        resp = handle_give_delay_request(user, client, 2,
                                         this_device=device,
                                         registration_request_code=None)

        assert resp == [{'success': False,
                        'status': 'INSUFFICIENT_PERMISSION',
                        'permission': 'GiveDelayActions'}]

    @patch('payg_loan_system.actions.give_delay.save_mentor_request')
    @db_session
    def test_valid_command(self, *args):
        user = AbstractUserFactory.create()
        device = DeviceAbstractFactory.create()
        client = device.contract.client

        patcher_2.start()
        resp = handle_give_delay_request(user, client, 2,
                                         this_device=device,
                                         registration_request_code=None)

        assert resp == [{'success': True,
                        'status': 'GIVE_DELAY_SUCCESS',
                        'client_id': client.id,
                        'contract_event_id': None,
                        'device_serial_number': device.composed_serial,
                        'contract_reference': device.contract.reference,
                        'acting_user_id': user.id,
                        'name': client.person.name,
                        'surname': client.person.surname,
                        'delayed_days': 2}]
        patcher_2.stop()
