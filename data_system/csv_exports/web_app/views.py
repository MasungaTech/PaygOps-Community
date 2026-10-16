from datetime import datetime, timedelta
import functools
from werkzeug.exceptions import NotFound
from shared.services.celery_queue_service import CeleryQueueService
from flask_login import login_required, current_user
from flask import redirect, request, flash, url_for, render_template, send_file
from pony import orm

from data_system.csv_exports.web_app import file_exporter
from data_system.csv_exports.services.send_file_request_maker_service import SendFileRequestMaker
from data_system.csv_exports.services.jwt_service import StaticDownloadKeyChecker
from survey_system.models.forms import Form
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt
from shared.helpers.authorizer import authorizer
from worker_app.tasks.backup_activity_log import backup_activity_log_now
from shared.services.translation_service import TranslationService
import config

if getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False):
    from mobile_sync_system.controllers.update_controller import UpdateController
else:
    UpdateController = None


def key_checker(func):
    @functools.wraps(func)
    def decorator_check_key(*args, **kwargs):
        key = request.args.get('key')
        if not key or StaticDownloadKeyChecker.check_key(key, ['ExportDataAdmin']) is not None:
            return 'Invalid token. '
        return func(*args, **kwargs)
    return decorator_check_key


def task_checker(task_name):
    def decorator(func):
        @functools.wraps(func)
        def decorator_check_task(*args, **kwargs):
            print("Is task "+str(task_name)+" running: "+str(CeleryQueueService.is_task_running(task_name)))
            if CeleryQueueService.is_task_running(task_name):
                return 'The data is currently being processed. Please, wait some minutes and try again.'
            return func(*args, **kwargs)
        return decorator_check_task
    return decorator


@file_exporter.route('/locales/<language>/paygops.lng.js')
@orm.db_session
def paygops_trad(language):
    return TranslationService.get_js_language_file_content(language)

@file_exporter.route('/exports/analytical_db_pg_dump')
@orm.db_session
@key_checker
def analytical_db_pg_dump_download():
    if config.REMOTE_ADB_ADDRESS:
        return redirect('https://'+config.REMOTE_ADB_ADDRESS+'/file/analytical_db_pg_dump_direct?key='+request.args.get('key'))
    response = send_file(config.ANALYTICAL_DB_BACKUP_PATH+config.ANALYTICAL_DB_POSTGRES_FILENAME)
    response.headers["Content-Disposition"] = 'attachment; filename=analytical_db_postgres.sql'
    return response

@file_exporter.route('/analytical_db_pg_dump_direct')
@orm.db_session
@key_checker
def analytical_db_pg_dump_download_direct():
    response = send_file(config.ANALYTICAL_DB_BACKUP_PATH+config.ANALYTICAL_DB_POSTGRES_FILENAME)
    response.headers["Content-Disposition"] = 'attachment; filename=analytical_db_postgres.sql'
    return response

@file_exporter.route('/exports/analytical_db_ssl_cert')
@orm.db_session
@key_checker
def analytical_db_ssl_cert_download():
    response = send_file(config.ANALYTICAL_DB_SSL_CERT)
    response.headers["Content-Disposition"] = 'attachment; filename=analytical_db.crt'
    return response

@file_exporter.route('/exports/analytical_db_ssl_cert_root_ca')
@orm.db_session
@key_checker
def analytical_db_ssl_cert_root_ca_download():
    response = send_file(config.ANALYTICAL_DB_ROOT_SSL_CERT)
    response.headers["Content-Disposition"] = 'attachment; filename=analytical_db_root_ca.crt'
    return response


@file_exporter.route('/exports/<string:export_name>_static')
@orm.db_session
@key_checker
def csv_export_static_url(export_name):
    if not export_name in SendFileRequestMaker.GENERATOR_FUNCTION_MAP:
        raise NotFound
    return SendFileRequestMaker.send(export_name, current_user)


@file_exporter.route('/exports/custom_forms_filter')
@login_required
@authorizer('ExportDataAdmin')
@orm.db_session
def custom_forms_data_download_filter():
    expiration = datetime.now()+timedelta(days=365)
    key = generate_jwt(current_user.id, ['ExportDataAdmin'], 'Solaris Offgrid', config.api_secret, expiration)
    forms = orm.select((s.id, s.name) for s in Form).order_by(2)
    forms_url = url_for('files.csv_export_static_url', export_name='custom_forms_data')
    return render_template('custom_forms_filter.html', api_key=key, forms_data=forms, forms_url=forms_url)


@file_exporter.route('/mobile_app_file')
@login_required
@orm.db_session
def get_latest_mobile_app():
    #controller = UpdateController()
    #latest_url = controller.get_url_of_latest_version()
    latest_url = 'https://play.google.com/store/apps/details?id=com.solarisoffgrid.agentapp.release&hl=en&gl=US&pli=1'
    return redirect(latest_url)


@file_exporter.route('/backup_activity_log')
@login_required
@orm.db_session
def backup_activity_log():
    if config.ENV_VAR != 'TEST':
        backup_activity_log_now()
    return redirect(url_for('index'))
