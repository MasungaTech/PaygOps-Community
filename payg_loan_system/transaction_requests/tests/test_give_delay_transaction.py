import uuid
import json
from pony.orm import db_session
from payg_loan_system.transaction_requests.services.give_delay_service import \
    GiveDelayTransactionService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator


class TestGiveDelayTransation:

    @db_session
    def test_give_delay_transaction(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        device = client.contracts.select().first().linked_device
        request = GiveDelayTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            device_serial=device.composed_serial,
            delayed_days=5,
            note='TEST'
        )

        assert request.type == 'give_delay'
        assert json.loads(request.request_data) == {
            'device_serial': device.composed_serial,
            'delayed_days': 5,
            'note': 'TEST',
            'send_sms_to_client': False
        }

        assert json.loads(request.answer_data)[0]['status'] == 'GIVE_DELAY_SUCCESS'
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == device
