from payg_loan_system.transaction_requests.services.reverse_repayment_service import \
    ReverseRepaymentService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class ReverseRepaymentTransactionResource(TransactionResource):

    service = ReverseRepaymentService
