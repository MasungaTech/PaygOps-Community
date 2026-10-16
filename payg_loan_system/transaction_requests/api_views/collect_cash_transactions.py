from payg_loan_system.transaction_requests.services.collect_cash_service import \
    CollectCashTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class CollectCashTransactionResource(TransactionResource):

    service = CollectCashTransactionService
