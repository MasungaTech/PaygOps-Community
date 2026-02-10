from datetime import datetime
from uuid import uuid1
from shared.services.celery_queue_service import CeleryQueueService
from worker_app.tasks.delayed_hook import delayed_hook
from shared.api_helpers.client_helpers.json_serialization_helpers import serialize_data_to_json
import json


def process_hook(hook_event_name, hook_data):
    if 'webhook_sent_datetime' in hook_data: #this means we already tried to send it
        return
    hook_data['webhook_sent_datetime'] = datetime.now() # We leave that here to know generation time
    # We now need to process hook in a task to avoid issues with db_session getting hook list
    data_json = serialize_data_to_json(hook_data)
    hook_data = json.loads(data_json)
    CeleryQueueService.execute_task(delayed_hook,
        event=hook_event_name,
        data=hook_data
    )


def add_hook_after_commit(db, name, data):
    print('Added hook: '+name)
    def new_hook():
        print('Executed hook: '+name)
        process_hook(name, data)
    hook_id = data.get('id', uuid1())
    db._get_cache().add_commit_hook(f'{name}-{hook_id}', new_hook)
