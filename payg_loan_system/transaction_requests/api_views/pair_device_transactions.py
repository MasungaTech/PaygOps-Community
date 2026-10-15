from payg_loan_system.transaction_requests.services.pair_device_service import \
    PairDeviceTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class PairDeviceTransactionResource(TransactionResource):

    service = PairDeviceTransactionService

