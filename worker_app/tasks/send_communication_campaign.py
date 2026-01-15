from pony.orm import db_session
from worker_app.worker_app import worker_app
from messages_system.services.communications_service import CommunicationsService
from shared.logger.loggers import LogAPI

log_api = LogAPI()


@worker_app.task()
def send_communication_campaign(*args, **kwargs):
    try:
        with db_session:
            CommunicationsService.send_campaign(*args, **kwargs)
    except Exception as e:
        log_api.FatalNoRequest(e)
