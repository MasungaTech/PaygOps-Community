from mock import patch
from pony.orm import db_session
from shared.helpers.client_creator import ClientCreator
from tests.factories.factories import AbstractUserFactory
from payg_loan_system.devices.factories import DeviceAbstractFactory
from payg_loan_system.actions.give_discount import give_discount, ContractRepaymentService
from payg_loan_system.contracts.services.tests.factories import ContractRepaymentFactory
patcher_2 = patch.object(ContractRepaymentService, 'give_units_discount', return_value=ContractRepaymentFactory.stub())


class TestGiveDiscount:

    @db_session
    def test_user_without_auth(self, api_client, good_api_key, *args):
        user = AbstractUserFactory.create(authorized=False)
        device = ClientCreator.create(api_client, good_api_key).contracts.select().first().linked_device

        resp = give_discount(acting_user=user,
                             discounted_units=2,
                             registration_request_code='FOO_CODE',
                             this_device=device)

        assert resp == [{'success': False,
                        'status': 'INSUFFICIENT_PERMISSION',
                        'permission': 'GiveDiscountActions'}]

    @patch('payg_loan_system.actions.give_discount.save_mentor_request')
    @db_session
    def test_valid_command(self, *args):
        user = AbstractUserFactory.create()
        device = DeviceAbstractFactory.create()

        patcher_2.start()
        resp = give_discount(acting_user=user,
                             discounted_units=2,
                             registration_request_code='FOO_CODE',
                             this_device=device)
        patcher_2.stop()

        assert resp[0]['success'] == True
        assert resp[0]['status'] == 'GIVE_DISCOUNT_SUCCESS'
        assert resp[0]['discounted_days'] == 2

