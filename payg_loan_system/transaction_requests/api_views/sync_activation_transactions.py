from payg_loan_system.transaction_requests.services.sync_activation_service import \
    SyncActivationTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class SyncActivationTransactionResource(TransactionResource):

    service = SyncActivationTransactionService
