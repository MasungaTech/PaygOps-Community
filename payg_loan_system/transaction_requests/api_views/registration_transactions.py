from payg_loan_system.transaction_requests.services.registration_service import \
    RegistrationTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class RegistrationTransactionResource(TransactionResource):

    service = RegistrationTransactionService
