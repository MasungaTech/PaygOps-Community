from payg_loan_system.transaction_requests.services.resume_contract_service import \
    ResumeContractTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class ResumeTransactionResource(TransactionResource):

    service = ResumeContractTransactionService