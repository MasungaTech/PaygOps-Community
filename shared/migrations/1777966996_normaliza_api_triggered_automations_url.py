from pony.orm import db_session
from app_builder_system.automations.models.automation_model import Automation


def _replace_path_suffix(url_value, from_suffix, to_suffix):
    if not isinstance(url_value, str):
        return url_value
    if not url_value.endswith(from_suffix):
        return url_value
    return f"{url_value[:-len(from_suffix)]}{to_suffix}"

@db_session
def up(db):
    for automation in Automation.select():
        trigger = automation.trigger or {}
        if trigger.get('type') != 'api':
            continue

        trigger_data = dict(trigger.get('data') or {})
        sync_url = trigger_data.get('synchronous')
        async_url = trigger_data.get('asynchronous')

        old_suffix = f"/run/{automation.uuid}"
        new_suffix = f"/automations/run/{automation.uuid}"

        new_sync_url = _replace_path_suffix(sync_url, old_suffix, new_suffix)
        new_async_url = _replace_path_suffix(async_url, old_suffix, new_suffix)

        if new_sync_url == sync_url and new_async_url == async_url:
            continue

        trigger_data['synchronous'] = new_sync_url
        trigger_data['asynchronous'] = new_async_url
        trigger = dict(trigger)
        trigger['data'] = trigger_data
        automation.trigger = trigger

@db_session
def down(db):
    for automation in Automation.select():
        trigger = automation.trigger or {}
        if trigger.get('type') != 'api':
            continue

        trigger_data = dict(trigger.get('data') or {})
        sync_url = trigger_data.get('synchronous')
        async_url = trigger_data.get('asynchronous')

        old_suffix = f"/automations/run/{automation.uuid}"
        new_suffix = f"/run/{automation.uuid}"

        new_sync_url = _replace_path_suffix(sync_url, old_suffix, new_suffix)
        new_async_url = _replace_path_suffix(async_url, old_suffix, new_suffix)

        if new_sync_url == sync_url and new_async_url == async_url:
            continue

        trigger_data['synchronous'] = new_sync_url
        trigger_data['asynchronous'] = new_async_url
        trigger = dict(trigger)
        trigger['data'] = trigger_data
        automation.trigger = trigger
