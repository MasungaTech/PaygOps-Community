"""
log_system.py: Contains the logging system, tracks events and errors and save them.
"""
import inspect
import os
from datetime import datetime
import traceback
import sys
import json
from types import TracebackType
from flask_login import current_user
from flask import render_template, request, current_app
from pony.orm import db_session
import config
from config import DATA_PATH, ENV_VAR
from shared.services.translation_service import TranslationService
import copy
from shared.logger.pretty_traceback import PrettyTraceBackService

GlobalLog = os.path.join(DATA_PATH, 'logs/global_log.txt')
ErrorLog = os.path.join(DATA_PATH, 'logs/error_log.txt')
ExceptionLog = os.path.join(DATA_PATH, 'logs/exception_log.txt')
LAST_ERROR_HTML = os.path.join(DATA_PATH, 'logs/last_error.html')


class Warning(Exception):
    """
    Warning Exception
    """
    pass


class Error(Exception):

    def __init__(self, *args, code=None, **kwargs):

        self.code = code or args[0] if args else ''
        self.description = args[0] if code and args else ''
        self.data = kwargs
        super().__init__(*args)

    def __str__(self):
        return self.code

    def get_message(self, language="EN"):
        raw_text = self.description or self.code
        from messages_system.services.message_service import MessageService
        try:
            template = MessageService.get_default_template(self.code, language, False)
            if template == self.code:
                raise KeyError()
            message, success = MessageService.format_template_if_valid(template, self.data)
            return message if success else raw_text
        except KeyError:
            force_format = self.data.get('force_format', False)
            if force_format:
                return TranslationService.ftext(raw_text, **self.data)
            return raw_text


class AcceptedWithProcessingError(Exception):
    def __init__(self, data):
        self.data = data
        super().__init__(data)

class AlreadyExistsError(Exception):

    def __init__(self, data):
        self.data = data
        super().__init__(data)

class RotatingFile(object):

    def __init__(self, filepath, max_file_size=200*1024*1024):
        self.ii = 1
        self.filepath = filepath
        self.max_file_size = max_file_size
        self.fh = None
        self.init()

    def init(self):
        if self.is_log_too_big():
            self.ii = 2
            if self.is_log_too_big():
                self.ii = 1
                self.clear()

    def is_log_too_big(self):
        if os.path.isfile(self.filename_template):
            return (os.stat(self.filename_template).st_size>self.max_file_size)
        else:
            self.clear()
            return False

    def rotate(self):
        if self.is_log_too_big():
            if (self.ii == 1):
                self.ii = 2
            else:
                self.ii = 1
            self.clear()

    def clear(self):
        file = open(self.filename_template, 'w+')
        file.write('')
        file.close()

    def write(self, text=""):
        file = open(self.filename_template, 'a')
        file.write(text)
        file.close()
        self.rotate()

    @property
    def filename_template(self):
        if self.ii == 1:
            return self.filepath
        parts = self.filepath.split('.')
        return "".join(parts[:-1])+ '_' + str(self.ii) + '.' + parts[-1]


class LogAPI:
    last_log_data = None

    @classmethod
    def _get_tb_from_frame(cls, f, tb=None):
        tb = TracebackType(tb_next=tb, tb_frame=f, tb_lasti=f.f_lasti, tb_lineno=f.f_lineno)
        if f.f_back:
            return cls._get_tb_from_frame(f.f_back, tb)
        return tb

    @classmethod
    def check_and_warn(cls, boolean_expression, message='Assertion Failed'):
        if not boolean_expression:
            cls.Warning(message)
            return False
        return True

    @classmethod
    def Event(cls, EventMessage):
        message = f'{datetime.now()}. Event: {EventMessage}\n'
        if ENV_VAR != 'TEST':
            cls._write_to_log(GlobalLog, message)
        print(message)

    @classmethod
    def Warning(cls, WarningMessage, other_data=None, no_pretty=False):
        message = f'{datetime.now()}. Warning: {WarningMessage}\n'
        tb = traceback.format_stack()[:-1]
        log_data = {
            'time': str(datetime.now()),
            'platform_url': config.PAYG_API_URL_BASE,
            'version': config.VERSION,
            'type': 'warning'
        }
        if other_data:
            log_data.update({'data': other_data})
        if ENV_VAR != 'TEST':
            try:
                log_data.update(cls._get_request_data())
            except:
                pass
        log_data['error'] = WarningMessage
        log_data['error_type'] = "Warning"
        log_data['traceback'] = tb + [WarningMessage]
        tb = cls._get_tb_from_frame(inspect.currentframe().f_back)
        if not no_pretty:
            log_data['trace_data'] = cls._get_pretty_traceback((Warning, Warning(WarningMessage), tb)) or log_data['traceback']
        cls._send_log_data_if_needed(log_data)
        if ENV_VAR != 'TEST':
            cls._write_to_log(GlobalLog, f'{message} | Data: {json.dumps(other_data)}')
        print(message)

    @classmethod
    def Error(cls, ErrorMessage):
        message = f'{datetime.now()}. Error: {ErrorMessage}\n'
        if ENV_VAR != 'TEST':
            cls._write_to_log(GlobalLog, message)
            cls._write_to_log(ErrorLog, message)
        print(message)

    @classmethod
    def Fatal(cls, exception):
        message = f'[Fatal] {datetime.now()}. Exception: {str(exception)}\n'
        log_data = {
            'time': str(datetime.now()),
            'platform_url': config.PAYG_API_URL_BASE,
            'version': config.VERSION,
            'type': 'exception'
        }
        log_data.update(cls._get_exception_data(exception))
        if ENV_VAR != 'TEST':
            cls._write_to_log(GlobalLog, message)
            cls._write_to_log(ErrorLog, message)
            try:
                log_data.update(cls._get_request_data())
            except:
                pass
        cls._send_log_data_if_needed(log_data)
        cls._store_exception_logs_if_needed(log_data)
        print(message)
        return log_data

    @classmethod
    def FatalNoRequest(cls, exception, extra_data={}, raise_if_test=False):
        message = f'{datetime.now()}. Exception (no request): {str(exception)}\n'
        if ENV_VAR != 'TEST':
            cls._write_to_log(GlobalLog, message)
            cls._write_to_log(ErrorLog, message)
        elif raise_if_test:
            raise exception
        log_data = {
            'time': str(datetime.now()),
            'platform_url': config.PAYG_API_URL_BASE,
            'version': config.VERSION,
            'type': 'exception_no_request'
        }
        log_data.update(cls._get_exception_data(exception))
        log_data.update(extra_data)
        cls._send_log_data_if_needed(log_data)
        print(message)
        cls._store_exception_logs_if_needed(log_data)
        return log_data

    @classmethod
    def _write_to_log(cls, filepath, message):
        try:
            writer = RotatingFile(filepath)
            message = message.encode('ascii', 'ignore').decode('ascii')
            writer.write(message)
        except Exception as e:
            print(f'Couldnt save log: {str(e)}')

    @classmethod
    def _store_exception_logs_if_needed(cls, log_data):
        if 'trace_data' in log_data:
            if os.getenv('ENV_VAR') == 'DEV' and log_data['error'] != 'Migration recursion limit exceeded.':
                with open(LAST_ERROR_HTML, "w") as f:
                    f.write(str(json.dumps(log_data)))
                print('More info: ..' + LAST_ERROR_HTML)
        if os.getenv('ENV_VAR') != 'TEST':
            log_data_2 = copy.deepcopy(log_data)
            log_data_2.pop('trace_data')
            cls._write_to_log(ExceptionLog, json.dumps(log_data_2)+'\n')
        else:
            print(str(log_data))

    @classmethod
    def _get_request_data(cls):
        if current_app.name == 'api_app':
            from core_system.users.services.current_user_service import get_current_api_user
            with db_session:
                user = get_current_api_user()
                data = {'user_name': user.full_name, 'user_id': user.id}
        elif current_app.name == 'mobile_sync_app':
            from shared.helpers.auth_helper import getCurrentUser
            with db_session:
                user = getCurrentUser()
                data = {'user_name': user.full_name, 'user_id': user.id}
        else:
            try:
                data = {'user_name': current_user.full_name, 'user_id': current_user.id}
            except:
                data = {'user_name': 'Unknown User', 'user_id': '0'}
        data.update({
            'user_agent': str(request.user_agent),
            'user_ip': str(request.environ.get('HTTP_X_REAL_IP', request.remote_addr)),
            'form': str(request.form),
            'data': str(request.data),
            'request': str(request),
            'request_dict': json.dumps(request.__dict__, default=str)
        })
        return data
    
    @classmethod
    def _clean_error(cls, error):
        error = str(error)
        ERRORS_TO_CLEAN = {
            'IntegrityError': 'DETAIL: ',
            'OptimisticCheckError': 'Changes: ',
            'UnrepeatableReadError: Value of ': 'for ',
            'violates not-null constraint': 'DETAIL: '
        }
        for error_type, error_string in ERRORS_TO_CLEAN.items():
            if error_type in error and error_string in error:
                error = error.split(error_string)[0]+error_string+'['+error.split(error_string)[1]+']'
        return error

    @classmethod
    def _get_exception_data(cls, exception):
        tb = traceback.format_exc().splitlines()
        exc_name = cls._clean_error(tb[-1])
        error = cls._clean_error(exception)
        data = {
            'error': error if not '500 Internal Server Error' in error else exc_name,
            'error_name': exc_name,
            'error_type': str(exception.__class__.__name__),
            'error_args': json.dumps(getattr(exception, 'args', []), default=str),
            'traceback': tb
        }
        try:
            data.update({
                'trace_data': cls._get_pretty_traceback()
            })
        except Exception as e:
            print('Issue getting exception data: '+str(e))
        return data

    @classmethod
    def _get_pretty_traceback(cls, exc_info=None):
        try:
            return PrettyTraceBackService.get_pretty_trace_object(exc_info)
        except Exception as e:
            cls.Warning(f'Unhandled exception in _get_pretty_traceback: {str(e)}', no_pretty=True)

    @classmethod
    def _send_log_data_if_needed(cls, log_data):
        # We only configure log shipping when not running local (where the URL would be None, defaulting to localhost)
        if config.is_production_server():
            data_copy = copy.deepcopy(log_data)
            del data_copy['time']
            if cls.last_log_data == data_copy:
                return
            cls.last_log_data = data_copy
            from shared.api_helpers.client_helpers.api_helper_object import APIHelper
            monitoring_api = APIHelper(config.monitoring_api_url, 'nokey')
            # We disable logging to avoid loop
            monitoring_api.delayed_post('/api/v1/error_logs/'+config.monitoring_api_key, data=log_data, log_error=False)


LogService = LogAPI() # This is temporary, we should remove all use of LogAPI as class method and just use it directly with logservice
