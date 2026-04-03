from shared.cache.redis_config import push_list_value
import json


class CustomHandlers:

    @staticmethod
    def mark_success(data=None, hook_name=None, hook_id=None):
        CustomHandlers._store_hook_report_data(
            report_type='success',
            hook_id=hook_id,
        )

    @staticmethod
    def hook_url_error(exception, full_url, params=None, data=None, auth_headers=None, hook_name=None, hook_id=None):
        CustomHandlers._store_hook_report_data(
            report_type='invalid_url',
            hook_url=full_url,
            hook_name=hook_name,
            hook_id=hook_id,
        )

    @staticmethod
    def hook_url_error_http(exception, full_url, params=None, data=None, auth_headers=None, hook_name=None, hook_id=None):
        details = f'Code: {exception.response.status_code}, Reason: {exception.response.reason}'
        CustomHandlers._store_hook_report_data(
            report_type=str(exception.response.status_code),
            error_details=details,
            hook_url=full_url,
            hook_name=hook_name,
            hook_id=hook_id,
        )

    @staticmethod
    def _store_hook_report_data(report_type='', error_details='', hook_name=None, hook_url=None, hook_id=None):
        hook_report_data = {
            'hook_id': hook_id,
            'hook_name': hook_name,
            'hook_url': hook_url,
            'type': report_type,
            'error_details': error_details
        }
        push_list_value('hook_reports', [json.dumps(hook_report_data)])