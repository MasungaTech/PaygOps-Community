# THIS ABSOLUTELY NEEDS TO BE FIRST
import config

import shared.helpers.database_hook
from shared.api_helpers.server_helpers.jwt_and_schema_verification import get_user_from_request
from shared.helpers.debugger import initialize_debugger
from flask import Flask, request, g
from flask_restful import Api
from flask_restful.utils import http_status_message
from flask_cors import CORS
from werkzeug.exceptions import BadRequest
from payg_loan_system.reversed_payments.api_views import PaymentReversalResource
from shared.api_helpers.server_helpers.api_initialization import initialize_api_system
from shared.database_mapper import DatabaseMapper
from shared.logger.loggers import LogAPI, Error
from shared.api_helpers.api_structure import API_STRUCTURE
from pony.orm import IsolationError
from shared.services.translation_service import TranslationService
from core_system.users.services.current_user_service import get_current_api_user
from pony import orm
from shared.logger.loggers import LogService
import time

LOGGER = LogAPI()

class ExtendedAPI(Api):

    def handle_error(self, e):
        data = {}
        code = getattr(e, 'code', 500)
        description = getattr(e, 'description', None) or http_status_message(code)
        if isinstance(e, Error):
            data = e.data
            code = e.code
            force_format = data.get('force_format', False)
            with orm.db_session:
                if force_format:
                    description = TranslationService.ftext(e.description or code, user=get_current_api_user(), **data)
                else:
                    description = TranslationService.ftext(e.description or code, user=get_current_api_user()) if e.description else e.get_message(language=TranslationService.get_language_for_user(get_current_api_user()))
            e = BadRequest(e.args[0])
        if code == 500 and not isinstance(e, IsolationError):
            LOGGER.Fatal(e)
        else:
            LOGGER.Error(str(code)+ ' Data: ' + str(data))
        setattr(e, 'data', {
            'error': code,
            'error_message': description,
            'error_data': data,
            'success': False
        })
        return super().handle_error(e)


initialize_debugger(5679)

api_app = Flask(__name__)
api = ExtendedAPI(api_app)
CORS(api_app)

# We setup the metrics
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics
from shared.monitoring.monitor_auth import monitor_auth
default_labels = {'serv': 'api', 'ver': config.VERSION}
metrics = GunicornInternalPrometheusMetrics(api_app, group_by='endpoint', path='/api/v1/pmetrics', default_labels=default_labels, metrics_decorator=monitor_auth.login_required)
metrics.info('app_info', 'API App', **default_labels)

from .api_version_check import api_info, api_health

for resource, path in API_STRUCTURE.items():
    api.add_resource(resource, config.API_PREFIX + path)
api.add_resource(PaymentReversalResource, '/reversed_payments/api/v1/payment_reversals', endpoint='payment_reversal_old')

initialize_api_system(api_app, config.secret_key, 'Solaris Offgrid')
from api_app.error_handler import *

@api_app.before_request
def load_user():
    if request.endpoint not in ['api_info', 'api_health', 'apikeyresource', 'newdatahookresource', 'prometheus_metrics'] and request.method != 'OPTIONS':
        get_user_from_request()


@api_app.before_request
def pageload_timer():
    request.environ['request_start_time'] = time.time()


@api_app.after_request
def pageload_timer_alert(response):
    # This can be empty in case of unauthorized request
    if request.environ.get('request_start_time'):
        load_time = (time.time() - request.environ['request_start_time'])
        if load_time > config.PAGELOAD_WARNING_THRESHOLD_API:
            LogService.Warning(f"API Response took [{load_time:.1f}] seconds")
    return response

DatabaseMapper.generate_map()
