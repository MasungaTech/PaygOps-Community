from pony.orm import db_session
from shared.helpers.client_creator import ClientCreator
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService


class TestReconciledPaymentsService:

    client = None

    @db_session
    def test_get_pending_reconciled_payments(self, api_client, good_api_key):
        client = self._get_client(api_client, good_api_key)
        contract = client.contracts.select().first()
        data = {
            "transaction_id": "Test-Pending-Rconciled-Payments",
            "sender_name": client.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(contract.offer.base_price_amount/2)
        }
        ClientCreator.post_payment(data, api_client, good_api_key)
        pending = contract.pending_reconciled_payment.select()
        assert pending.count() == 1
        assert pending.first().contract_pending_repayment == contract
        assert pending.first().linked_payment.Reference == 'Test-Pending-Rconciled-Payments'
        assert pending.first().amount == contract.offer.base_price_amount/2
        assert contract.pending_amount == contract.offer.base_price_amount/2

    @classmethod
    def _get_client(cls, api_client, good_api_key):
        return cls.client or ClientCreator.create(api_client, good_api_key)
