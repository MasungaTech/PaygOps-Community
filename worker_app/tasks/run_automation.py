from pony import orm
from worker_app.worker_app import worker_app
from shared.logger.loggers import LogAPI
import config

log_api = LogAPI()


"""
Celery task to run enterprise automations.

In OSS / non-enterprise builds the `app_builder_system` package is not
available, so this module must *not* import it at import time. We therefore
guard the import and make the task a no-op when enterprise features are
disabled.
"""

if getattr(config, "ENABLE_ENTERPRISE_FEATURES", False):
    from app_builder_system.automations.services.automation_run_service import (
        AutomationRunService,
    )

    @worker_app.task
    @orm.db_session
    def run_automation_from_uuid(automation_uuid, data=None, user=None, return_log=False):
        try:
            AutomationRunService.run_automation_from_uuid(
                automation_uuid, data, user, return_log
            )
        except Exception as e:
            log_api.FatalNoRequest(e)
else:

    @worker_app.task
    @orm.db_session
    def run_automation_from_uuid(automation_uuid, data=None, user=None, return_log=False):
        # Enterprise automations are disabled in this edition; log and skip.
        log_api.Warning(
            f"run_automation_from_uuid called in OSS edition; "
            f"automation {automation_uuid} will not be executed."
        )