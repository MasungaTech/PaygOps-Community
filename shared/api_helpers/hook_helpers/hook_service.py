from shared.services.base_getter_service import BaseGetterService
from shared.model.hook_model import Webhook
from pony import orm
import config
from shared.logger.loggers import Error
from shared.logger.loggers import LogAPI
from shared.api_helpers.client_helpers.api_helper_object import APIHelper
from shared.services.webhook_log_service import WebhookLogService

class WebhookService(BaseGetterService):

    @classmethod
    def process_hook(cls, hook_event_name, hook_data):
        if hook_event_name not in config.ALLOWED_HOOKS:
            LogAPI.Warning(f'Proccessed hook {hook_event_name} is not subscribable')
        LogAPI.Event('Procesing Hook: '+hook_event_name+' ; '+str(hook_data))
        hooks = cls.get_hooks_for_event(hook_event_name)
        if hooks:
            LogAPI.Event(f'Sending Hook {hook_event_name} to worker for Hook IDs/URLs: {str([h.target_url for h in hooks])}')
        for hook in hooks:
            hook_id = hook.id
            hook_url = hook.target_url
            WebhookLogService.insert(hook_event_name, hook_url, hook_data)
            hook_api = APIHelper(hook_url, '')
            try:
                handler = ['hook_url_error', {'hook_name': hook_event_name, 'hook_id': hook_id}]
                custom_handlers = {
                    'HTTPError': ['hook_url_error_http', {'hook_name': hook_event_name, 'hook_id': hook_id}],
                    'MissingSchema': handler,
                    'InvalidSchema': handler,
                    'InvalidURL': handler,
                    'ConnectionError': handler,
                    'Timeout': handler
                }
                if hook.failures_since_last_success > 0:
                    custom_handlers.update({
                        "success": ['mark_success', {'hook_name': hook_event_name, 'hook_id': hook_id}]
                    })
                if config.AUTOMATED_TESTING != '1' and not hook.automation:
                    hook_api.delayed_post('', 
                        data=hook_data, 
                        custom_handlers=custom_handlers,
                        timeout=config.HOOK_TIMEOUT
                    )
                if hook.automation:
                    hook_api.delayed_get('', custom_handlers=custom_handlers, timeout=config.HOOK_TIMEOUT)
            except Exception as error:
                LogAPI.Error(
                    'Error in process_hook. Error: {}. URL: {} ; Data: {}'.format(
                        repr(error),
                        repr(hook_url),
                        repr(hook_data)))

    @classmethod
    def get_hooks_for_event(cls, event_name):
        test = cls._test_mode()
        return orm.select(h for h in Webhook if h.event == event_name and h.active and h.test == test)[:]
    
    @classmethod
    def _hook_already_exists(cls, event, target_url, automation=None):
        test = cls._test_mode()
        return orm.select(h for h in Webhook if h.event == event and h.target_url == target_url and h.test == test and h.automation == automation).exists()
    
    @classmethod
    def _test_mode(cls):
        return True if config.is_dev_mode() else False

    @classmethod    
    def get_filtered_objects(cls, current_user, **kwargs):
        test = cls._test_mode()
        hooks = Webhook.select().filter(lambda h: h.test == test)
        return hooks
    
    @classmethod
    def _add_from_data_and_user(cls, data, user):
        if cls._hook_already_exists(event=data.get('event'), target_url=data.get('target_url')):
            raise Error('A webhook for the same event and URL is already registered.')
        new_hook = Webhook(
            event=data.get('event'),
            target_url=data.get('target_url'),
            active=data.get('active', True),
            test=data.get('test', cls._test_mode()),
            created_by_user=user
        )
        automation_uuid = data.get('automation')
        if automation_uuid:
            if not config.ENABLE_ENTERPRISE_FEATURES:
                raise Error('AUTOMATIONS_DISABLED')
            from app_builder_system.automations.services.automation_service import AutomationService
            new_hook.automation = AutomationService.get_from_user_and_properties(user, uuid=automation_uuid)
        return new_hook
    
    @classmethod
    def _edit_from_data_and_user(cls, hook, data, user):
        automation_uuid = data.get('automation')
        automation_service = None
        if automation_uuid:
            if not config.ENABLE_ENTERPRISE_FEATURES:
                raise Error('AUTOMATIONS_DISABLED')
            from app_builder_system.automations.services.automation_service import AutomationService
            automation_service = AutomationService
        if 'active' in data:
            if not hook.active and data.get('active'):
                hook.failures_since_last_success = 0
            hook.active = data.get('active')
        if 'test' in data:
            hook.test = data['test']
        if 'event' in data or 'target_url' in data or 'automation' in data:
            e = data.get('event', hook.event)
            t = data.get('target_url', hook.target_url)
            automation_lookup = None
            if automation_uuid:
                automation_lookup = automation_service.get_from_user_and_properties(user, uuid=automation_uuid)
            if cls._hook_already_exists(event=e, target_url=t, automation=automation_lookup):
                return hook
        if 'event' in data:
            hook.event = data['event']
        if 'target_url' in data:
            hook.target_url = data['target_url']
        if automation_uuid:
            hook.automation = automation_service.get_from_user_and_properties(user, uuid=automation_uuid)
        return hook
    
    @classmethod
    def _delete_from_object_and_user(cls, hook, user):
        hook.delete()

