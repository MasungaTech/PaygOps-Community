from flask_login import login_required, current_user
from pony.orm import db_session
from flask import render_template, flash, redirect, url_for
from shared.helpers.authorizer import authorizer
from . import administration
from payg_loan_system.devices.device_api.device_api_sync_service import DeviceGlobalSyncService
import config
from shared.services.settings_service import SettingsService
from shared.services.celery_queue_service import CeleryQueueService
from datetime import datetime


@administration.route('/sync_owned_devices')
@login_required
@authorizer('ViewPaygoDevices')
@db_session
def sync_owned_devices_route():
    device_syncs = DeviceGlobalSyncService.get_last_sync()
    date_to_ignore = datetime(1970, 1, 1).date()
    return render_template('owned_device_synced.html', device_syncs=device_syncs, date_to_ignore=date_to_ignore)


@administration.route('/sync_owned_devices/all')
@login_required
@authorizer('ViewPaygoDevices')
@db_session
def sync_owned_all_devices_route():
    from worker_app.tasks.sync_owned_devices import sync_owned_devices
    if config.is_dev_mode():
        flash('In a demo or development platform only the LDC device API is supported.')
    if CeleryQueueService.is_task_running('sync_owned_devices'):
        flash('The devices are already being synchronised in the background, please wait until it is finished. ')
    else:
        CeleryQueueService.execute_task(sync_owned_devices)
        flash('The new devices are now being synchronised in the background, '
                'please wait a few minutes and come back to this page to see the number of new devices synced. ')
    return redirect(url_for('admin.sync_owned_devices_route'))
