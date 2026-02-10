from pony import orm
from worker_app.worker_app import worker_app
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_api_sync_service import DeviceGlobalSyncService
from payg_loan_system.devices.model.device import Device
from datetime import datetime


# This syncs the activation on devices in the cloud
@worker_app.task
@orm.db_session
def force_sync_devices():
    now = datetime.now()
    all_devices = orm.select(d for d in Device if d.ActiveUntil > now)
    count = all_devices.count()
    done = 0
    for device in all_devices:
        DeviceAPIService.sync_device_activation(device)
        done += 1
        if done % 100 == 0:
            print(f'Synced {done}/{count} devices')


# This syncs the device parameters (e.g. units supported, monitoring supported, etc.)
@worker_app.task
@orm.db_session
def force_sync_device_parameters(device_type=None):
    all_devices = orm.select(d for d in Device if d.type != 'NPG')
    if device_type:
        all_devices.filter(lambda d: d.type == device_type)
    count = all_devices.count()
    done = 0
    for device in all_devices:
        DeviceGlobalSyncService.update_device_parameters(device)
        done += 1
        if done % 100 == 0:
            print(f'Synced {done}/{count} devices parameters')
