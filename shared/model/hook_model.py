from pony.orm import Required, Optional, composite_key
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from core_system.core_entities import db
import config


class Webhook(db.Entity, ModelDefinitionMixin):

    event = Required(str)
    target_url = Required(str)
    active = Required(bool, default=True)
    test = Required(bool)
    failures_since_last_success = Required(int, default=0, volatile=True)
    created_by_user = Optional('User', column='created_by_user')

    # When enterprise features are enabled, this is a proper relation to the
    # Automation entity defined in the enterprise modules. In OSS-only mode we
    # still map the underlying FK column as a plain integer so that:
    # - Pony doesn't try to resolve a missing Automation entity
    # - Existing code accessing hook.automation continues to work (it will be
    #   an int or None instead of an Automation instance, but OSS paths should
    #   never rely on non-None values here).
    if config.ENABLE_ENTERPRISE_FEATURES:
        automation = Optional('Automation', column='automation')
    else:
        automation = Optional(int, column='automation')

    composite_key(event, target_url)

    @classmethod
    def get_model_definition(cls, op=None, **kwargs):
        return {
            'properties': {
                "id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the webhook",
                    "value": lambda o: o.id
                },
                "event": {
                    "type": "string",
                    "example": "client_registered",
                    "enum": config.ALLOWED_HOOKS,
                    "description": "The name of the event in PaygOps that will trigger the hook to the `target_url`",
                    "value": lambda o: o.event
                },
                "target_url": {
                    "type": "string",
                    "format": "uri",
                    "example": "https://myapp.com/notify_me",
                    "description": "The URL to which the data should be sent in case of the `event` happening",
                    "value": lambda o: o.target_url
                },
                "active": {
                    "type": "boolean",
                    "example": True,
                    "description": "Whether the hook is active or not",
                    "value": lambda o: o.active
                },
                "test": {
                    "type": "boolean",
                    "example": False,
                    "description": "Whether the hook is a test hook or not. Only test hooks work on test platforms and only non-test hook work on regular platforms.",
                    "value": lambda o: o.test
                },
                "failures_since_last_success": {
                    "type": "number",
                    "example": 0,
                    "description": "The number of time the hook failed to contact the server since the last time it worked. This number is approximate as it might count several times in case of retries.",
                    "value": lambda o: o.failures_since_last_success
                },
            },
            'view_allowed': ["id", "event", "target_url", "active", "test", "failures_since_last_success"],
            'view_required': [],
            'edit_allowed': ["active", "test", "event", "target_url"],
            'edit_required': [],
            'create_allowed': ["event", "target_url", "active", "test"],
            'create_required': ["event", "target_url"]
        }