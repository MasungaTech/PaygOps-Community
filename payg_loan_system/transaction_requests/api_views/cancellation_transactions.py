from payg_loan_system.transaction_requests.services.cancellation_service import \
    CancelContractTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class CancelTransactionResource(TransactionResource):

    service = CancelContractTransactionService