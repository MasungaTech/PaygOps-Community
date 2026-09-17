import uuid
import json
from pony.orm import db_session
from payg_loan_system.transaction_requests.services.default_service import \
    DefaultTransactionService
from payg_loan_system.transaction_requests.services.undo_default_service import \
    UndoDefaultTransactionService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator
from shared.services.settings_service import SettingsService


class TestDefaultAndUndoDefaultTransation:

    @db_session
    def test_default_and_undo_default_transaction(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        device = client.contracts.select().first().linked_device
        request = DefaultTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            device_serial=device.composed_serial
        )
        SettingsService.set_setting('ContractDeviceRestrictions', 'require_device')
        assert request.type == 'default'
        assert json.loads(request.request_data) == {
            'device_serial': device.composed_serial,
            'note': None,
            'request_code': None,
            'send_sms_to_client': False
        }
        for answer in json.loads(request.answer_data):
            assert answer['success']
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == device

        request = UndoDefaultTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=device.contract.reference,
            device_serial=device.composed_serial
        )

        assert request.type == 'undo_default'
        assert json.loads(request.request_data) == {
            'contract_reference': device.contract.reference,
            'device_serial': device.composed_serial,
            'note': None,
            'request_code': None,
            'send_sms_to_client': False
        }
        assert json.loads(request.answer_data)[0]['success']
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == device
