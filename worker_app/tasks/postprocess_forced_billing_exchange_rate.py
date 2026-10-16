from pony.orm import db_session
from worker_app.worker_app import worker_app
import config


@worker_app.task
@db_session
def postprocess_forced_billing_exchange_rate():
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return
    from enterprise_features.services.billing_service import BillingService
    BillingService.postprocess_forced_billing_exchange_rate()
