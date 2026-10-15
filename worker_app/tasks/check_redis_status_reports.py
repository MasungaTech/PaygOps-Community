from pony.orm import db_session
from config import FAILED_WEBHOOKS_THRESHOLD
from worker_app.worker_app import worker_app
from shared.logger.loggers import LogService
from core_system.core_entities import db as mdb
from shared.cache.redis_config import get_list, delete_list_value
from messages_system.services.notifications_service import NotificationsService
from shared.helpers.html_safety_helper import join_markup, safe_var
import json


@worker_app.task
@db_session
def check_redis_status_reports(*args, **kwargs):
    status_reports = get_list('hook_reports')
    print(f'Found {len(status_reports)} status reports')
    for report_raw in status_reports:
        report = json.loads(report_raw)
        hook = mdb.Webhook.get(id=report.get('hook_id'))
        # If no hook it was removed or comes form system
        if hook:
            hook_name = hook.event
            full_url = hook.target_url
            if hook.failures_since_last_success != 0:
                if report.get('type') == 'success':
                    hook.failures_since_last_success = 0
                else:
                    hook.failures_since_last_success += 1
                if hook.failures_since_last_success >= FAILED_WEBHOOKS_THRESHOLD:
                    hook.active = False
            else:
                # We only notify at the first failure after a success
                if not report.get('type') == 'success':
                    hook.failures_since_last_success += 1
                if report.get('type') == 'invalid_url':
                    NotificationsService.add_notification(
                        text=join_markup(
                            'The web hook "',
                            safe_var(hook_name),
                            '" has a subscription from an invalid url (',
                            safe_var(full_url),
                            '). Please check the hooks configuration to avoid any loss of information. ',
                        )
                    )
                else:
                    NotificationsService.add_notification(
                        text=join_markup(
                            'The web hook "',
                            safe_var(hook_name),
                            '" has a subscription from an invalid url (',
                            safe_var(full_url),
                            '). The server returned the following error: ',
                            safe_var(report.get('error_details')),
                            ' Please check the hooks configuration to avoid any loss of information.',
                        )
                    )
        delete_list_value('hook_reports', report_raw)