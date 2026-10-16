import uuid
import json
from pony.orm import db_session
from payg_loan_system.transaction_requests.services.deregister_service import \
    DeRegisterTransactionService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator


class TestDeregisterTransation:

    @db_session
    def test_deregister_transaction(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        device = client.contracts.select().first().linked_device
        request = DeRegisterTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            device_serial=device.composed_serial
        )

        assert request.type == 'deregister'
        assert json.loads(request.request_data) == {
            'device_serial': device.composed_serial,
            'note': None,
            'request_code': None,
            'send_sms_to_client': False
        }

        assert json.loads(request.answer_data)[0]['status'] == 'CLIENT_DEREGISTRATION_SUCCESS'
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == device
