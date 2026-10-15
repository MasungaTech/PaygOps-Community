import uuid
import json
from pony.orm import db_session, commit
from payg_loan_system.transaction_requests.services.sync_activation_service import \
    SyncActivationTransactionService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator


class TestSyncActivationTransation:

    @db_session
    def test_sync_activation_transaction(self, api_client, good_api_key):
        commit()
        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        device = client.contracts.select().first().linked_device
        request = SyncActivationTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            device_serial=device.composed_serial
        )

        assert request.type == 'sync_activation'
        assert json.loads(request.request_data) == {
            'device_serial': device.composed_serial,
            'request_code': None,
            'send_sms_to_client': False
        }

        assert json.loads(request.answer_data)[0]['status'] == 'ACTIVATION_REQUEST_SUCCESS' # We force this when manual sync
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == device
