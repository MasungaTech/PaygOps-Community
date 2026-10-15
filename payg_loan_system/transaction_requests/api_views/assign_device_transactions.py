from payg_loan_system.transaction_requests.services.assign_device_service import \
    AssignDeviceTransactionService
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource


class AssignDeviceTransactionResource(TransactionResource):

    service = AssignDeviceTransactionService
