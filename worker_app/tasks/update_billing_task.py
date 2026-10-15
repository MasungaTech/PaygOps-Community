from worker_app.worker_app import worker_app
from pony.orm import db_session
import config


@worker_app.task
@db_session
def update_billing_task():
    if config.DISABLE_HEAVY_TASKS or not config.ENABLE_ENTERPRISE_FEATURES:
        return 
    from enterprise_features.services.billing_service import BillingService
    BillingService.update_billing()