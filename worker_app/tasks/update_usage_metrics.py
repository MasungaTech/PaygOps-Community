from pony.orm import db_session
from worker_app.worker_app import worker_app
from core_system.core_entities import db
from payg_loan_system.devices.services.device_metrics_service import DeviceMetricsService


@worker_app.task
@db_session
def update_usage_metrics_for_device(device_id):
    device = db.Device.get(id=device_id)
    if device:
        DeviceMetricsService.update_device_metrics(device)


@worker_app.task
@db_session
def update_usage_metrics_for_all_applicable_devices():
    DeviceMetricsService.update_all_device_metrics()
