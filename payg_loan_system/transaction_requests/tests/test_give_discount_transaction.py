import uuid
import json
from pony.orm import db_session
from payg_loan_system.transaction_requests.services.give_discount_service import \
    GiveDiscountTransactionService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator


class TestGiveDiscountTransation:

    @db_session
    def test_give_discount_transaction(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        device = client.contracts.select().first().linked_device
        request = GiveDiscountTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            device_serial=device.composed_serial,
            discounted_days=5,
            discounted_amount=None,
            note='TEST'
        )

        assert request.type == 'give_discount'
        assert json.loads(request.request_data) == {
            'device_serial': device.composed_serial,
            'discounted_amount': None,
            'discounted_days': 5,
            'discounted_units': None,
            'note': 'TEST',
            'send_sms_to_client': False
        }

        assert json.loads(request.answer_data)[0]['status'] == 'GIVE_DISCOUNT_SUCCESS'
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == device

        request = GiveDiscountTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            device_serial=device.composed_serial,
            discounted_days=None,
            discounted_amount=10,
            note='TEST'
        )

        assert request.type == 'give_discount'
        assert json.loads(request.request_data) == {
            'device_serial': device.composed_serial,
            'discounted_amount': 10,
            'discounted_days': None,
            'discounted_units': None,
            'note': 'TEST',
            'send_sms_to_client': False
        }

        assert json.loads(request.answer_data)[0]['status'] == 'GIVE_DISCOUNT_SUCCESS_AMOUNT'
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == device
