from worker_app.worker_app import worker_app
from payg_loan_system.devices.device_api.device_api_sync_service import DeviceGlobalSyncService
from pony import orm


@worker_app.task
@orm.db_session
def sync_owned_devices():
    DeviceGlobalSyncService.sync_all_new_owned_devices()
