from payg_loan_system.transaction_requests.services.change_offer_service import \
    ChangeOfferTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class ChangeOfferTransactionResource(TransactionResource):

    service = ChangeOfferTransactionService
