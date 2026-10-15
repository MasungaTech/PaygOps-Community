from pony import orm
from worker_app.worker_app import worker_app
from shared.helpers.form_helpers import dateTimePickerToStandard
from payg_loan_system.payments.services.orphaned_payment_service import OrphanedPaymentService
from shared.logger.loggers import LogAPI

log_api = LogAPI()


@worker_app.task
def reconcile_orphaned_payments(from_date, to_date, exclude_reverted=True):
    try:
        from_date = dateTimePickerToStandard(from_date)
        to_date = dateTimePickerToStandard(to_date, '23:59')
        OrphanedPaymentService.auto_route_orphaned_payments(from_date, to_date, exclude_reverted)
    except Exception as e:
        log_api.FatalNoRequest(e)