from payg_loan_system.transaction_requests.services.pause_contract_service import \
    PauseContractTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class PauseTransactionResource(TransactionResource):

    service = PauseContractTransactionService