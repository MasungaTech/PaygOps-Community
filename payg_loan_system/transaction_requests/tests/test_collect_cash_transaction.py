import uuid
import json
from pony.orm import db_session
from payg_loan_system.transaction_requests.services.collect_cash_service import \
    CollectCashTransactionService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator


class TestCollectCashTransaction:

    @db_session
    def test_collect_cash_transaction(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        device = client.contracts.select().first().linked_device
        request = CollectCashTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            device_serial=device.composed_serial,
            amount=10,
            note='test note'
        )

        assert request.type == 'collect_cash'
        assert json.loads(request.request_data) == {
            'device_serial': device.composed_serial,
            'contract_mobile_uuid': '',
            'amount': 10,
            'send_sms_to_client': False,
            'note': 'test note'
        }       
        for answer in json.loads(request.answer_data):
            assert answer['success']
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == device


    @db_session
    def test_collect_cash_transaction_for_lead(self):

        lead = ClientCreator.create_lead()
        user = User.get(username="super_admin@test.com")
        request = CollectCashTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            lead_id=lead.id,
            amount=15,
            note='test note'
        )

        assert request.type == 'collect_cash'
        assert json.loads(request.request_data) == {
            'lead_id': lead.id,
            'amount': 15,
            'send_sms_to_client': False,
            'note': 'test note'
        }
        for answer in json.loads(request.answer_data):
            assert answer['success']
        assert request.user == user
        assert request.success
        assert request.client is None
        assert request.device is None
        assert lead.deposit_paid
        assert lead.reconciled_payments.count() == 2
        assert lead.already_paid == 15
        assert lead.get_cash_account().get_total_payments() == \
            lead.get_cash_account().get_total_reconciled() == 15
