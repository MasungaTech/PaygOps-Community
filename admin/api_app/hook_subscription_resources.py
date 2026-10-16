from flask_restful import request
from werkzeug.exceptions import BadRequest, NotFound
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from pony.orm import db_session
from shared.api_helpers.documented_resource import DocumentedResource, get_error_example, API_ERROR_SCHEMA
import config
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from shared.api_helpers.hook_helpers.hook_service import WebhookService, Webhook
from core_system.users.services.current_user_service import get_current_api_user


class AllWebhooksResource(BaseAPIResourceAll):

    ADD_SERVICE = WebhookService
    LIST_SERVICE = WebhookService
    ADD_PERMISSION = 'CreateAPITokenAdmin'
    LIST_PERMISSION = 'CreateAPITokenAdmin'
    MODEL = Webhook
    
    OBJECT_NAME = 'Webhooks'
    TAG = 'Webhooks'

class IndividualWebhooksResource(BaseAPIResourceIndividual):

    GET_SERVICE = WebhookService
    EDIT_SERVICE = WebhookService
    DELETE_SERVICE = WebhookService
    GET_PERMISSION = 'CreateAPITokenAdmin'
    EDIT_PERMISSION = 'CreateAPITokenAdmin'
    DELETE_PERMISSION = 'CreateAPITokenAdmin'
    MODEL = Webhook

    OBJECT_NAME = 'Webhooks'
    TAG = 'Webhooks'


URL_SCHEMA = {
    "description": "The URL that should be notified when `event` is raised",
    "type": "string",
    "format": "uri",
    "example": "https://myapp.com/notify_me"
}

EMPTY_SCHEMA = {
    "application/json": {
        "schema": {
            "description": "Empty object",
            "type": "object",
            "properties": {}
        },
        "example": {}
    }
}


class SubscribeHookResource(DocumentedResource):

    META = {
        "post": {
            "deprecated": True,
            "summary": "Create Webhook subscription (DEPRECATED)",
            "description": "Create a new webhook subscription for an speficic URL.",
            "tags": ["Webhooks"],
            "permissions": ['AddAPIHook'],
            "schema": {
                "properties": {
                    "target_url": URL_SCHEMA,
                    "event": {
                        "description": "The event in PaygOps that will make `target_url` to be notified",
                        "type": "string",
                        "enum": config.ALLOWED_HOOKS,
                        "example": "new_lead_payment"
                    }
                },
                "required": ["target_url", "event"],
                "aditionalProperties": False
            },
            "responses": {
                201: {
                    "description": "Webhook subscription created",
                    "content": EMPTY_SCHEMA
                },
                400: {
                    "description": "Badly formated request",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(code=400, message='Invalid event')
                        }
                    }
                },
                409: {
                    "description": "The URL is already registered for that `event`",
                    "content": EMPTY_SCHEMA
                }
            }
        }
    }

    @verify(**META['post'])
    @db_session
    def post(self):
        hook_data = request.json
        if not hook_data:
            return {'error': 'No data provided'}, 404
        hook_event_name = hook_data['event']
        if hook_event_name in config.ALLOWED_HOOKS:
            WebhookService.add_from_data_and_user(hook_data, get_current_api_user())
            return {}, 201
        else:
            return {}, 409


class UnsubscribeHookResource(DocumentedResource):

    META = {
        "post": {
            "deprecated": True,
            "summary": "Remove Webhook subscription (DEPRECATED)",
            "description": "Remove an existing webhook subscription for an speficic URL.",
            "tags": ["Webhooks"],
            "permissions": ['DeleteAPIHook'],
            "schema": {
                "properties": {
                    "target_url": URL_SCHEMA
                },
                "required": ["target_url"],
                "aditionalProperties": False
            },
            "responses": {
                200: {
                    "description": "Webhook subscription deleted",
                    "content": EMPTY_SCHEMA
                },
                400: {
                    "description": "Badly formated request",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(code=400, message='target_url is required')
                        }
                    }
                },
                404: {
                    "description": "The URL was not found",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(message='The hook subscription was not found')
                        }
                    }
                }
            }
        }
    }

    @verify(**META['post'])
    @db_session
    def post(self):
        hook_data = request.json
        if not hook_data:
            return {'error': 'No data provided'}, 404
        hook_url = hook_data.get('target_url', None)
        if not hook_url:
            raise BadRequest('target_url is required')
        hooks_to_delete = Webhook.select().filter(lambda h: h.target_url == hook_url)
        if hooks_to_delete.count() == 0:
            raise NotFound('The hook subscription was not found')
        for hook in hooks_to_delete:
            hook.delete()
        return {'success': True}, 200
