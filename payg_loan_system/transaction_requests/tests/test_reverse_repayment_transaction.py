import uuid
import json
from pony.orm import db_session
from payg_loan_system.transaction_requests.services.reverse_repayment_service import \
    ReverseRepaymentService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator


class TestReverseRepaymentTransation:

    @db_session
    def test_reverse_repayment_transaction(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        ClientCreator.post_payment({
            "transaction_id": "RepaymentTestPayment"+str(client.id),
            "sender_name": client.full_name,
            "sender_msisdn": client.person.contactPhone.number,
            "amount": 10
        }, api_client, good_api_key)
        repayment = client.contracts.select().first().repayments.select()[:][1]
        request = ReverseRepaymentService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            repayment_id=repayment.id
        )

        assert request.type == 'reverse_repayment'
        assert json.loads(request.request_data) == {
            'repayment_id': repayment.id,
            'send_sms_to_client': False
        }

        assert json.loads(request.answer_data)[0]['status'] == 'PAYMENT_REVERSED_SETTING_ENABLED'
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == repayment.contract.linked_device
