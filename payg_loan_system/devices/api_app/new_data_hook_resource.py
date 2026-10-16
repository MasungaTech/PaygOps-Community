from pony import orm
from flask_restful import Resource, request
from payg_loan_system.devices.model.device import Device
from shared.services.celery_queue_service import CeleryQueueService
from worker_app.tasks.update_usage_metrics import update_usage_metrics_for_device

class NewDataHookResource(Resource):

    @orm.db_session
    def post(self, uuid):
        device = Device.get(new_data_hook_uuid=uuid)
        if device:
            CeleryQueueService.execute_task(update_usage_metrics_for_device, device.id)
