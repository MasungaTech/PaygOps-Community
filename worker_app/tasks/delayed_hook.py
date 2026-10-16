from worker_app.worker_app import worker_app
from pony import orm
from shared.api_helpers.hook_helpers.hook_service import WebhookService


@worker_app.task(priority=3)
def delayed_hook(event, data=None):
    with orm.db_session:
        WebhookService.process_hook(event, data)