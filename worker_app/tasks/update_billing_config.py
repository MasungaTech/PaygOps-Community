from worker_app.worker_app import worker_app
from pony import orm
import config


@worker_app.task
@orm.db_session
def update_billing_config_task():
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return
    from enterprise_features.services.billing_service import BillingService
    BillingService.update_billing_config()
