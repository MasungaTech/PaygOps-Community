from worker_green_app.worker_green_app import worker_green_app
from shared.logger.loggers import LogAPI
from shared.api_helpers.client_helpers.custom_handlers import CustomHandlers
import requests
import os

IS_SECONDARY = os.getenv('SPLIT_SERVER_MODE', 'STANDARD') == 'SECONDARY'
MAIN_SERVER_IP = os.getenv('MAIN_SERVER_IP')

@worker_green_app.task()
def delayed_get_request(full_url, params=None, auth_headers=None, log_error=True, custom_handlers=None, timeout=60):
    if custom_handlers is None:
        custom_handlers = {}
    try:
        if 'gateway:8002' in full_url and IS_SECONDARY:
            full_url = full_url.replace('gateway:8002', f'{MAIN_SERVER_IP}:30104')
        LogAPI().Event('Delayed GET to ' + str(full_url))
        response = requests.get(full_url, params=params, headers=auth_headers, timeout=timeout)
        response.raise_for_status()
    except Exception as exception:
        LogAPI.Event('Delayed GET failed once, retrying... ')
        try:
            response = requests.get(full_url, params=params, headers=auth_headers, timeout=timeout)
            response.raise_for_status()
        except Exception as exception:
            handled = False
            for error_type in custom_handlers:
                if not hasattr(requests.exceptions, error_type):
                    if error_type != 'success':
                        LogAPI.Warning(f'Error type {error_type} is not part of the requests exceptions module')
                    continue
                error_class = getattr(requests.exceptions, error_type)
                if error_type != 'success' and isinstance(exception, error_class):
                    handler = custom_handlers[error_type][0]
                    data = custom_handlers[error_type][1]
                    getattr(CustomHandlers, handler)(exception, full_url, params, data, auth_headers, **data)
                    LogAPI.Event('Delayed GET failed twice, logging.')
                    handled = True
            if not handled:
                LogAPI.Event('Delayed GET failed twice, stopping.')
                if log_error:
                    extra_data = {
                        'url': full_url,
                        'params': params
                    }
                    LogAPI.FatalNoRequest(exception, extra_data=extra_data)
                print(repr(exception))
    else:
        if custom_handlers.get('success'):
            handler_data = custom_handlers.get('success')
            handler = handler_data[0]
            data = handler_data[1]
            CustomHandlers.mark_success(**data)
