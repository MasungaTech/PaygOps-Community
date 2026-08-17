from payg_loan_system.transaction_requests.services.deregister_service import \
    DeRegisterTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class DeRegisterTransactionResource(TransactionResource):

    service = DeRegisterTransactionService
