from payg_loan_system.transaction_requests.services.swap_device_service import \
    SwapDeviceTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class SwapDeviceTransactionResource(TransactionResource):

    service = SwapDeviceTransactionService
