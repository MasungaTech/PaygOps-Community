import json
import csv
from uuid import uuid1
from werkzeug.exceptions import NotFound
from io import StringIO
from admin.services.api_caller_service import APICallerService
from admin.web_app.bulk_upload import BULK_UPLOADS_DATA
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from core_system.operational_entities.services.operational_entity_reorganization_service import OperationalEntityReorganizerService
from flask import abort, send_file, Response, stream_with_context, jsonify
from admin.services.doc360_service import Doc360Service
from constants import ALLOWED_HOOKS, DATA_EXPORTS_CONFIG, NUMBER_OF_BILLING_TIERS, BILLING_ORDERED_FEATURE_KEYS
from payg_loan_system.offers.models import OfferType
from shared.api_helpers.documented_resource import DocumentedResource
from shared.api_helpers.hook_helpers.hook_service import WebhookService
from shared.helpers.db_helpers import searchable_text
from shared.logger.loggers import Error, LogAPI
from admin.api_docs_services import APIDocsService
from datetime import datetime, timedelta
from shared.api_helpers.api_structure import API_STRUCTURE, API_STRUCTURE_NAMES
from werkzeug.exceptions import MethodNotAllowed
from flask_login import login_required, current_user
from flask import request, render_template, flash, get_flashed_messages, redirect, url_for, make_response
from pony.orm import db_session, select, left_join
import time

from shared.helpers.auth_helper import encode_password, db
from shared.helpers.authorizer import authorizer
from shared.helpers.pagination import Pagination, ResultSet
from shared.helpers.clock import Clock
from shared.helpers.form_helpers import dateTimePickerToStandard, isoDateTimeToStandard
from shared.helpers.select2 import render
from shared.model.billing import Bill, BillingType
from shared.services.background_task_base import BackgroundTask
from shared.services.settings_service import SettingsService
from shared.services.activity_log_service import ActivityLogGetter, ActivityLogSorter
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt

from data_system.services.custom_dashboard_service import CustomDashboardService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from core_system.users.models.user_model import User
from messages_system.services.notifications_service import NotificationsService, NotificationsSorter
from tests.support.mock_query import MockQuery
from worker_app.tasks.analyse_api_caller import analyse_api_caller

# We keep those imported so that they appear in the list
from worker_app.tasks.update_analytical_db import update_analytical_db
from worker_app.tasks.compute_csv_exports import compute_csv_data_now
from worker_app.tasks.update_cached_data import update_cached_data_now
from worker_app.tasks.check_cache_coherence import check_cached_data_now
from worker_app.tasks.send_payment_reminder_messages import send_payment_reminder_sms_now
from worker_app.tasks.check_db_health import check_db_health, kill_long_running_queries
from worker_app.tasks.fix_first_last_answers import fix_first_answer_old, fix_last_answer_old, fix_answer_person_first_last
from worker_app.tasks.background_migrations_task import background_migration_task
from worker_app.tasks.reconcile_orphaned_payments import reconcile_orphaned_payments
from worker_app.tasks.update_contract_status import update_contract_status
from worker_app.tasks.autoreconciliation import autoreconciliate, autoreconciliate_week
from worker_app.tasks.fix_payment_processing import fix_payment_processing
from worker_app.tasks.check_db_consistency import check_db_consistency
from worker_app.tasks.migrate_payments_wrongly_marked_as_not_orphaned import migrate_payments_wrongly_marked_as_not_orphaned
from worker_app.tasks.db_reindex import reindex
from worker_app.tasks.db_vacuum import db_vacuum
from worker_app.tasks.check_repayments_coherence import check_repayments_coherence
from worker_app.tasks.periodic_file_backup_to_azure import backup_files_not_previously_uploaded
from worker_app.tasks.force_sync_devices import force_sync_devices, force_sync_device_parameters
from worker_app.tasks.check_adb import check_adb_running, check_adb_coherence
from shared.services.celery_queue_service import CeleryQueueService
from data_system.analytical_db.analytical_db import analytical_db as adb
from shared.services.audit_log_service import AuditLogService, AuditLogSorter

import config
import os
from . import administration

if config.ENABLE_ENTERPRISE_FEATURES:
    from worker_app.tasks.update_billing_config import update_billing_config_task
    from worker_app.tasks.update_billing_task import update_billing_task
    from enterprise_features.views.billing_views import *
    from enterprise_features.views.package_installer_views import *
    from enterprise_features.views.metabase_views import *

@administration.route('/user_settings', methods=["GET", "POST"])
@login_required
@db_session
def user_settings():
    user = db.User.get(id=current_user.id)
    if request.method == 'POST':
        if request.form['action'] == 'change_pass':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            new_password_confirm = request.form.get('new_password_confirm')
            if current_user.password == encode_password(old_password):
                if new_password == new_password_confirm:
                    user.password = encode_password(new_password)
                    flash('Pass saved.')
                else:
                    flash('The two passwords are different. Operation aborted.')
            else:
                flash('Old password wrong!')
        elif request.form['action'] == 'change_preferences':
            user.show_notifications = request.form.get('show_notifications', False)
            sms_language = request.form.get('sms_language', user.person.sms_language)
            if sms_language not in config.AVAILABLE_USERS_SMS_LANGUAGES:
                raise Error('INVALID_SMS_LANGUAGE')
            user.person.sms_language = sms_language
    return render_template('user_settings.html', user=user)


@administration.route('/', methods=["GET", "POST"])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def admin():
    return render_template('admin.html', Message=get_flashed_messages())


@administration.route('/entity_level_adjustment_tool', methods=["GET", "POST"])
@login_required
@authorizer('SuperAdmin')
@db_session
def entity_level_adjustment_tool():
    if request.method == "POST":
        try:
            OperationalEntityReorganizerService.move_up_entities(int(request.form['level']))
        except Error as e:
            flash(e.get_message())

    def get_entity_data(entity):
        return {
            'name': entity.name,
            'children': [get_entity_data(c) for c in entity.children]
        }

    oe_config = SettingsService.get_setting('OperationalEntities')
    base_levels = {
        i: oe_config[i]['names'] for i in range(
            OperationalEntitiesHelper.get_max_level_enabled(), -1, -1
        )
    }

    disabled = OperationalEntitiesHelper.get_max_level_enabled() == 4

    return render_template(
        'entity_level_adjustment_tool.html',
        base_levels=base_levels,
        disabled=disabled
    )


@administration.route('/preview_entity_adjustment', methods=["GET"])
@login_required
@authorizer('SuperAdmin')
@db_session
def preview_entity_adjustment():
    level = request.args.get('level')
    if level:
        preview = OperationalEntityReorganizerService.preview(int(level))
        max_level = OperationalEntitiesHelper.get_max_level_enabled()+1
    else:
        preview = OperationalEntityReorganizerService.get_current_structure()
        max_level = OperationalEntitiesHelper.get_max_level_enabled()
    return render_template('entities_structure_schema.html', schema=preview, max_level=max_level)


@administration.route('/view_full_hierarchy', methods=["GET"])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def view_full_hierarchy():
    preview = OperationalEntityReorganizerService.get_current_structure(limit=None)
    max_level = OperationalEntitiesHelper.get_max_level_enabled()
    return render_template('view_full_hierarchy.html', schema=preview, max_level=max_level)


@administration.route('/api_docs', methods=["GET"])
@login_required
@authorizer('ViewAPIDocumentation')
@db_session
def api_docs():
    return render_template('api_docs.html', full_width=True, DO_NOT_TRANSLATE=True)


@administration.route('/api_docs.json', methods=["GET"])
@login_required
@db_session
def api_docs_json():
    content = APIDocsService.generate_api_docs(current_user)
    response = make_response(content)
    response.headers["Content-Disposition"] = 'attachment; filename=api_docs.json'
    response.headers["Content-type"] = "application/json"
    return response


@administration.route('/data_exports', methods=["GET", "POST"])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def data_exports():
    # Only include exports for models that are actually available in the analytical DB.
    # This avoids showing (or breaking on) enterprise-only exports when enterprise features are disabled.
    available_entities = adb.entities
    exports = {
        key: [
            data['name'],
            available_entities[data['model']]._description_,
            data.get('tag', '')
        ]
        for key, data in DATA_EXPORTS_CONFIG.items()
        if data['model'] in available_entities
    }
    key = ''
    if current_user.can_access('ExportDataAdmin'):
        expiration = datetime.now()+timedelta(days=365)
        key = generate_jwt(current_user.id, ['ExportDataAdmin'], 'Solaris Offgrid', config.api_secret, expiration)
    return render_template('file_exports.html', Message=get_flashed_messages(), api_key=key, exports=exports, custom_form_desc=adb.entities["Question_Answers"]._description_)


@administration.route('/analytical_db', methods=["GET"])
@login_required
@authorizer('ExportDataAdmin')
@db_session
def analytical_db():
    if current_user.can_access('ExportDataAdmin'):
        expiration = datetime.now()+timedelta(days=365)
        key = generate_jwt(current_user.id, ['ExportDataAdmin'], 'Solaris Offgrid', config.api_secret, expiration)
    return render_template('analytical_db.html', api_key=key)


@administration.route('/notifications', methods=["GET", "POST"])
@login_required
@authorizer(['SeeAllNotificationsAdmin', 'SeeHubNotificationsAdmin'])
@db_session
def notifications():

    from_date = request.form.get('from_date', request.args.get('from_date', ''))
    from_time = request.form.get('from_time', request.args.get('from_time', '00:00'))
    to_date = request.form.get('to_date', request.args.get('to_date', ''))
    to_time = request.form.get('to_time', request.args.get('to_time', '23:59'))

    params = 'from_date={}&from_time={}&to_date={}&to_time={}'.format(from_date,
                                                                      from_time,
                                                                      to_date,
                                                                      to_time)
    pagination = Pagination.generate(request,
                                     params=params,
                                     default_sort='time:desc')

    notfs = NotificationsService.get_list(current_user, search=pagination.search)

    if from_date:
        d = dateTimePickerToStandard(from_date, from_time)
        d = Clock.localize_to_utc(d)
        notfs = notfs.filter(lambda n: n.time >= d)

    if to_date:
        d = dateTimePickerToStandard(to_date, to_time)
        d = Clock.localize_to_utc(d)
        notfs = notfs.filter(lambda n: n.time <= d)

    pagination.objects = NotificationsSorter.sort(notfs, pagination.sort)
    NotificationsService.update_last_seen(current_user.reload())

    return render_template('notifications.html',
                           pagination=pagination,
                           from_date=from_date,
                           from_time=from_time,
                           to_date=to_date,
                           to_time=to_time)


# It is called registry and not log on purpose to avoid triggering Cloudflare security
@administration.route('/access_registry', methods=["GET", "POST"])
@login_required
@authorizer(['ViewActivityLogAdmin', 'SuperAdmin'])
@db_session
def access_log():
    log_numbers = [1,2,3,4]
    return render_template('access_log.html', log_numbers=log_numbers)

@administration.route('/webhook_log', methods=["GET", "POST"])
@login_required
@authorizer(['ViewActivityLogAdmin', 'SuperAdmin'])
@db_session
def webhook_log():
    log_numbers = [1,2,3,4]
    return render_template('webhook_log.html', log_numbers=log_numbers)


@administration.route('/download_access_registry/<log_number>', methods=["GET", "POST"])
@login_required
@authorizer(['ViewActivityLogAdmin', 'SuperAdmin'])
@db_session
def download_access_log(log_number):
    if log_number == '0':
        log_file = config.ACCESS_LOG_PATH
    else:
        # Only rotated logs are compressed
        log_file = f'{config.ACCESS_LOG_PATH}.{log_number}.gz'
    try: 
        return send_file(log_file, as_attachment=True) 
    except FileNotFoundError: 
        flash('There is not yet a log file to download')
        return redirect(url_for('admin.access_log'))
    
@administration.route('/download_webhook_log/<log_number>', methods=["GET", "POST"])
@login_required
@authorizer(['ViewActivityLogAdmin', 'SuperAdmin'])
@db_session
def download_webhook_log(log_number):
    if log_number == '0':
        log_file = config.WEBHOOK_LOG_PATH
    else:
        log_file = f'{config.WEBHOOK_LOG_PATH}.{log_number}.gz'
    try:
        return send_file(log_file, as_attachment=True)
    except FileNotFoundError:
        flash('There is not yet a log file to download')
        return redirect(url_for('admin.webhook_log'))
    

@administration.route('/audit_log', methods=["GET", "POST"])
@login_required
@authorizer(['ViewActivityLogAdmin', 'SuperAdmin'])
@db_session
def audit_log():
    action = request.args.get('action', '')
    object_type_url = request.args.get('object_type', '')
    
    # Convert URL format to class name for internal processing
    URL_TO_CLASS_MAPPING = {
        f'l{level}_entity': entity_class.__name__
        for level, entity_class in OperationalEntitiesHelper.CLASSES.items()
        if level >= 0  # Exclude client_groups (level -1)
    }
    object_type = URL_TO_CLASS_MAPPING.get(object_type_url, object_type_url)
    
    object_id = request.args.get('object_id', '')
    user_id = request.args.get('user_id', '')
    search_field = request.args.get('search_field', '')
    search_value = request.args.get('search_value', '')
    request_uuid = request.args.get('request_uuid', '')

    if search_value and not object_id:
        flash('You must specify an object ID to search')
        return redirect(url_for('admin.audit_log'))

    td = timedelta(days=365) if object_id or request_uuid else (timedelta(hours=6) if SettingsService.get_setting('StressMode') else timedelta(days=1))
    default_start_date = datetime.now()-td
    default_start_date = default_start_date.isoformat().replace("+00:00", "Z")
    from_date = request.args.get('from_date', default_start_date)
    to_date = request.args.get('to_date')

    pagination = Pagination.generate(request, default_sort='time:desc')
    logs = AuditLogService.get_list(
        from_time=from_date, 
        to_time=to_date, 
        action=action, 
        user_id=user_id, 
        object_type=object_type, 
        object_id=object_id, 
        search_field=search_field, 
        search_value=search_value,
        request_uuid=request_uuid
    )
    pagination.objects = AuditLogSorter.sort(logs, pagination.sort)

    users = select(u for u in User).order_by(lambda u: u.full_name)
    select2 = {
        'users': {
            'items': users,
            'text': 'full_name',
            'selected': User.get(id=user_id) if user_id and user_id != 'NONE' else None
        }
    }

    object_types = {}
    for e in db.entities:
        if e not in AuditLogService.EXLUDED_TYPES:
            object_types[e] = AuditLogService.get_object_type_name(e)
    for e in AuditLogService.EXTRA_TYPES:
        object_types[e] = AuditLogService.get_object_type_name(e)
    
    # Convert operational entity keys to URL format (l0_entity, l1_entity, etc.)
    OPERATIONAL_ENTITY_MAPPING = {
        entity_class.__name__: f'l{level}_entity'
        for level, entity_class in OperationalEntitiesHelper.CLASSES.items()
        if level >= 0  # Exclude client_groups (level -1)
    }
    
    # Replace keys for operational entities
    for class_name, url_format in OPERATIONAL_ENTITY_MAPPING.items():
        if class_name in object_types:
            object_types[url_format] = object_types.pop(class_name)
    
    get_user = lambda id: User.get(id=id)
    return render(
        'audit_log.html',
        pagination=pagination,
        object_type=object_type_url,  # Use URL format for template
        object_id=object_id,
        action=action,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        select2=select2,
        get_user=get_user,
        object_types=object_types,
        too_many_results=False,
        type_name=AuditLogService.get_object_type_name,
        search_field=search_field,
        search_value=search_value,
        request_uuid=request_uuid
    )



@administration.route('/activity_log', methods=["GET", "POST"])
@login_required
@authorizer(['ViewActivityLogAdmin', 'SuperAdmin'])
@db_session
def legacy_activity_log():

    default_start_date = datetime.now()-(timedelta(hours=5.5) if SettingsService.get_setting('StressMode') else timedelta(days=1))
    default_start_date = default_start_date.isoformat().replace("+00:00", "Z")
    actionfilter = request.args.get('actionfilter', '')
    userfilter = request.args.get('userfilter', '')
    from_date = request.args.get('from_date', default_start_date)
    to_date = request.args.get('to_date')

    pagination = Pagination.generate(request, default_sort='time:desc')

    logs = ActivityLogGetter.get_list(current_user)
    users = select(u for u in User).order_by(lambda u: u.full_name)

    if pagination.search:
        logs = logs.filter(lambda l: pagination.search in l.path)

    if actionfilter and actionfilter != 'ALL':
        if actionfilter == 'VIEW':
            logs = logs.filter(lambda l: l.method == 'GET')
        else:
            logs = logs.filter(lambda l: l.method != 'GET')

    selected_user = None
    if userfilter:
        if userfilter != 'NONE':
            selected_user = int(userfilter)
            logs = logs.filter(lambda l: selected_user == l.user)
        else:
            logs = logs.filter(lambda l: not l.user)

    from_date_utc = None
    if from_date:
        d = isoDateTimeToStandard(from_date)
        from_date_utc = Clock.localize_to_utc(d, naive=True)
        logs = logs.filter(lambda l: l.time >= from_date_utc)

    to_date_utc = datetime.now()
    if to_date:
        d = isoDateTimeToStandard(to_date)
        to_date_utc = Clock.localize_to_utc(d, naive=True)
        logs = logs.filter(lambda l: l.time <= to_date_utc)

    too_many_results = False
    if SettingsService.get_setting('StressMode'):
        if (len(pagination.search) < 3 and
            (not from_date_utc or to_date_utc-from_date_utc > timedelta(hours=6)) and
            not selected_user and
            (not actionfilter or actionfilter == 'ALL')
            ):

            too_many_results = True
            logs = MockQuery([])

    pagination.objects = ActivityLogSorter.sort(logs, pagination.sort)

    select2 = {
        'userfilter': {
            'items': users,
            'text': 'full_name'
        }
    }

    get_user = lambda id: User.get(id=id)

    return render(
        'activity_log.html',
        pagination=pagination,
        actionfilter=actionfilter,
        user_id=userfilter,
        from_date=from_date,
        to_date=to_date,
        select2=select2,
        get_user=get_user,
        too_many_results=too_many_results
    )

@administration.route('/webhooks', methods=["GET", "POST"])
@login_required
@authorizer('AddAPIHook')
@db_session
def webhooks():
    webhook_list = WebhookService.get_list().order_by(lambda h: h.id)
    return render_template(
            'webhooks.html',
            webhooks=webhook_list,
            events=[(e, e) for e in ALLOWED_HOOKS]
    )


@administration.route('/tasks_queue', methods=["GET", "POST"])
@login_required
@authorizer('SuperAdmin')
def tasks_queue():
    from data_system.analytical_db.analytical_db import analytical_db
    registered_tasks = CeleryQueueService.get_registered_tasks()
    registered_tasks_select = {}
    for task in registered_tasks:
        registered_tasks_select[task] = task.split('.')[-1]
    registered_tasks_select['delete_and_run_analytical_db'] = 'delete_and_run_analytical_db'

    if request.method == 'POST':
        task_name = request.form.get('task')
        try:
            params = json.loads(request.form.get('params') or '{}')
        except json.JSONDecodeError as error:
            flash(f'Error: {error}')
        else:
            if task_name == 'delete_and_run_analytical_db':
                # analytical_db.disconnect()
                analytical_db.drop_all_tables(with_all_data=True)
                analytical_db.create_tables()
                CeleryQueueService.execute_task(update_analytical_db)
            else:
                CeleryQueueService.execute_task_by_name(task_name, **params)
            time.sleep(1)

    tasks = CeleryQueueService.get_all_tasks()

    with db_session:
        return render_template(
            'task_manager.html',
            tasks=tasks,
            task_number=len(tasks),
            ts=datetime.now().timestamp(),
            registered_tasks=registered_tasks_select
        )


@administration.route('/tasks_queue/kill/live/<task_id>', methods=["GET", "POST"], defaults={'live': 'live'})
@administration.route('/tasks_queue/kill/queued/<task_id>', methods=["GET", "POST"], defaults={'live': 'queued'})
@administration.route('/tasks_queue/kill/<task_id>', methods=["GET", "POST"], defaults={'live': None})
@login_required
@authorizer('SuperAdmin')
@db_session
def tasks_queue_kill(task_id, live=None):
    if config.ENV_VAR == 'TEST': return redirect(url_for('admin.tasks_queue'))
    if live == 'live':
        CeleryQueueService.kill_live_task(task_id)
        flash(f'Task {task_id} is being killed')
    elif live == 'queued':
        CeleryQueueService.kill_queued_tasks([task_id])
        flash(f'Task {task_id} is being killed')
    else:
        if task_id == 'purge_live':
            CeleryQueueService.purge_live_tasks()
            flash('Purged all queued tasks')
        elif task_id == 'purge_queued':
            CeleryQueueService.purge_queued_tasks()
            flash('Purged all queued tasks')
        elif task_id == 'purge_unacked':
            CeleryQueueService.purge_unacked_tasks()
            flash('Purged all queued tasks')
        elif task_id == 'test':
            check_cached_data_now.delay()
            compute_csv_data_now.delay()
            compute_csv_data_now.delay()
            compute_csv_data_now.delay()
            update_analytical_db.delay()
            update_cached_data_now.delay(volatile=True)
            update_cached_data_now.delay(volatile=True)
            update_cached_data_now.delay(volatile=True)
            flash('Created test tasks')
        elif task_id == 'groom':
            CeleryQueueService.groom_queue()
            flash('Groomed queue')
        else:
            flash('Unknown query!')
    time.sleep(1)
    return redirect(url_for('admin.tasks_queue'))


@administration.route('/tags', methods=["GET"])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def tags_editor():
    from core_system.client.services.client_tag_getter import ClientTagService
    from payg_loan_system.devices.services.device_tag_getter import DeviceTagService

    tags = ClientTagService.get_list(current_user)
    device_tags = DeviceTagService.get_list(current_user)
    return render_template(
        'tags_editor.html',
        tags=tags,
        device_tags=device_tags
    )


@administration.route('/doc360_login', methods=["GET"])
@login_required
@db_session
def doc360_login():
    login_link = Doc360Service.get_login_link(current_user)
    return redirect(login_link)
    

@administration.route('/api_caller', methods=["GET"])
@administration.route('/api_caller/<string:uuid>', methods=["GET", "POST"])
@login_required
@authorizer('APICallerAdmin')  
@db_session
def api_caller(uuid=None):

    actions, subactions = APICallerService.get_action_list(current_user)
    action = request.args.get('action')
    subaction = request.args.get('subaction')
    if not uuid:
        if request.method == 'POST':
            raise MethodNotAllowed
        else:
            uuid = str(uuid1())
    
    task_service = BackgroundTask(uuid, 'api_caller', BULK_UPLOADS_DATA)
    if action:
        task_service.action = action+(':'+subaction if subaction else '')

    if request.method == 'POST':
        if request.form.get('cancel'):
            task_service.cancel()
            
            action=request.form.get('action')
            subaction=request.form.get('subaction')
            return redirect(url_for('admin.api_caller', action=action, subaction=subaction))
        if request.form.get('process'):
            task_service.process()
        elif 'csv_file' in request.files:
            try:
                task_service.upload_file(
                    request.files['csv_file'],
                    headers=request.form.get('headers')=='true',
                    unordered=request.form.get('unordered')=='true'
                )
                task_service.user = current_user.id
                task_service.user_ip = str(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
                task_service.user_agent = str(request.user_agent)
                task_service.request = {
                    'user_agent': str(request.user_agent),
                    'remote_addr': request.remote_addr,
                    'environ': {
                        'HTTP_X_REAL_IP': request.environ.get('HTTP_X_REAL_IP')
                    }
                }
                subaction = request.form.get('subaction')
                task_service.action = request.form.get('action') + (':'+subaction if subaction else '')
            except Error as error:
                LogAPI.Fatal(error)
                flash(error.args[0])
    
    return render_template(
        'api_caller.html',
        actions=actions,
        subactions=subactions,
        action=action,
        subaction=subaction,
        task=task_service
    )

@administration.route('/api_caller/docs/<string:action>', methods=["GET"])
@login_required
@authorizer('APICallerAdmin')
@db_session
def api_caller_docs(action=None):
    if not '_' in action: raise Error('Invalid Action')
    docs = APICallerService.get_action_docs(action, current_user)
    return render_template('api_caller_docs.html', docs=docs, action=action)


@administration.route('/api_caller_csv_template/<string:action>', methods=["GET"])
@login_required
@authorizer('APICallerAdmin')  
@db_session
def api_caller_csv_template(action):
    if not '_' in action: raise Error('Invalid Action')

    subaction = None
    if ':' in action:
        action, subaction = action.split(':')
    resource_name, method = action.split("_")
    if '-' in method:
        method, option = method.split("-")
    resource = API_STRUCTURE_NAMES.get(resource_name)
    if method not in resource.ALLOWED_API_CALLER:
        raise NotFound
    docs = resource.docs_get_metadata()[method]

    columns = []
    examples = []
    restricted = resource.SUBACTIONS[method][subaction]['properties'] if subaction else None
    excluded = resource.API_CALLER_GENERATORS.get(method, {}).keys()

    def example(ex, type):
        return ex if type != 'array' else f'"{",".join(map(str, ex))}"'
    
    if docs['parameters']:
        for prop in docs['parameters']:
            if (not restricted or prop['name'] in restricted) and prop['name'] not in excluded:
                columns.append(prop['name']+('*' if prop['required'] else ''))
                examples.append(prop['example'])
    if docs['requestBody'] and docs['requestBody']['schema'].get('properties'):
        for prop, data in docs['requestBody']['schema']['properties'].items():
            if not data.get('deprecated') and not (data.get('type') == 'object' or (data.get('type') == 'array' and data.get('items', {}).get('type') == 'object')):
                if (not restricted or prop in restricted) and prop not in excluded:
                    columns.append(prop+('*' if prop in docs['requestBody']['schema'].get('required', []) else ''))
                    examples.append(example(data['example'] if not data.get('enum') else data['enum'][0], data.get('type')))
    if docs['requestBody'] and docs['requestBody']['schema'].get('oneOf'):
        for prop, data in docs['requestBody']['schema']['oneOf'][int(option)-1]['properties'].items():
            if not data.get('deprecated') and not (data.get('type') == 'object' or (data.get('type') == 'array' and data.get('items', {}).get('type') == 'object')):
                if (not restricted or prop in restricted) and prop not in excluded:
                    columns.append(prop+('*' if prop in docs['requestBody']['schema'].get('required', []) else ''))
                    examples.append(example(data['example'] if not data.get('enum') else data['enum'][0], data.get('type')))

    content = render_template(
        'api_caller_csv_template.jinja2',
        columns=columns,
        examples=examples
    )
    response = make_response(content)
    response.headers["Content-Disposition"] = 'attachment; filename='+(subaction or docs['summary'])+'_bulk.csv'
    response.headers["Content-type"] = "text/csv"
    return response


@administration.route('/training', methods=["GET"])
@login_required
@db_session
def training():
    return render_template('training.html')



