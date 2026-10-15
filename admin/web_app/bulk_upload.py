from time import sleep
from shared.services.background_task_base import BackgroundTask
from worker_app.tasks.analyse_api_caller import analyse_api_caller
import config
from . import administration
from pony.orm import db_session
from flask_login import login_required, current_user
from shared.logger.loggers import Error, LogAPI
from werkzeug.exceptions import MethodNotAllowed, NotFound
from uuid import uuid1
from flask import render_template, request, redirect, url_for, flash

from worker_app.tasks.analyse_bulk_devices import analyse_bulk_devices
from worker_app.tasks.analyse_bulk_stock_movements import analyse_bulk_stock_movements
from worker_app.tasks.analyse_bulk_payments import analyse_bulk_payments
from worker_app.tasks.analyse_bulk_operational_entities import analyse_bulk_operational_entities
from worker_app.tasks.analyse_bulk_users import analyse_bulk_users
from worker_app.tasks.analyse_bulk_lead_generators import analyse_bulk_lead_generators
from worker_app.tasks.analyse_bulk_edit_client_groups import analyse_bulk_edit_client_groups
from worker_app.tasks.analyse_bulk_edit_clients import analyse_bulk_edit_clients
from worker_app.tasks.analyse_bulk_edit_leads import analyse_bulk_edit_leads


BULK_UPLOADS_DATA = {
    'stock_movements': ['Stock Movements', analyse_bulk_stock_movements],
    'devices': ['Devices', analyse_bulk_devices],
    'payments': ['Payments', analyse_bulk_payments],
    'operational_entities': ['Operational Entities', analyse_bulk_operational_entities],
    'users': ['Users', analyse_bulk_users],
    'lead_generators': ['Lead Generators', analyse_bulk_lead_generators],
    'client_groups': ['Client Groups', analyse_bulk_edit_client_groups],
    'edit_leads': ['Edit Leads', analyse_bulk_edit_leads],
    'edit_clients': ['Edit Clients', analyse_bulk_edit_clients],
    'api_caller': ['Actions', analyse_api_caller],
}

if config.ENABLE_ENTERPRISE_FEATURES:
    from worker_app.tasks.analyse_bulk_tasks import analyse_bulk_tasks
    BULK_UPLOADS_DATA['tasks'] = ['Tasks', analyse_bulk_tasks]


@administration.route('/bulk_upload/<string:entity>', methods=['GET'])
@administration.route('/bulk_upload/<string:entity>/<string:uuid>', methods=['GET', 'POST'])
@login_required
@db_session
def bulk_upload_task_view(entity, uuid=None):

    if not entity in BULK_UPLOADS_DATA:
        raise NotFound

    if not uuid:
        if request.method == 'POST':
            raise MethodNotAllowed
        else:
            uuid = str(uuid1())

    task_service = BackgroundTask(uuid, entity, config=BULK_UPLOADS_DATA)
    if request.method == 'POST':
        if request.form.get('cancel'):
            task_service.cancel()
            return redirect(url_for('admin.bulk_upload_task_view', entity=entity))
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
            except Error as error:
                LogAPI.Fatal(error)
                flash(error.args[0])
    return render_template('bulk_upload_template.html', task=task_service)


@administration.route('/bulk_upload/status/<string:uuid>', methods=['GET'])
@login_required
@db_session
def add_bulk_status(uuid):
    action = request.args.get("action")
    subaction = request.args.get("action")

    task_service = BackgroundTask(uuid, config=BULK_UPLOADS_DATA)
    return render_template(
        'add_bulk_status.html',
        task=task_service,
        action=action,
        subaction=subaction
    )
