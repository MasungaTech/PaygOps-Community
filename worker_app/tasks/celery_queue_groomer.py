from worker_app.worker_app import worker_app
from shared.services.celery_queue_service import CeleryQueueService
from shared.logger.loggers import LogAPI

log_api = LogAPI()



@worker_app.task
def celery_queue_groomer():
    try:
        CeleryQueueService.groom_queue()
    except Exception as e:
        log_api.FatalNoRequest(e)
    try:
        CeleryQueueService.kill_long_running_tasks()
    except Exception as e:
        log_api.FatalNoRequest(e)

@worker_app.task
def celery_queue_alerter():
    try:
        CeleryQueueService.check_long_running_tasks()
    except Exception as e:
        log_api.FatalNoRequest(e)
    try:
        CeleryQueueService.check_queue_length()
    except Exception as e:
        log_api.FatalNoRequest(e)
