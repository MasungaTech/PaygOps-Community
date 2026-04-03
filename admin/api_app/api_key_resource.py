from werkzeug.exceptions import Unauthorized
from config import ENV_VAR
from constants import FLOAT_OPTIONAL_OPTIONS
from shared.api_helpers.documented_resource import API_ERROR_SCHEMA, get_error_example
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt_for_user
from shared.helpers.auth_helper import encode_password
from core_system.users.services.user_getter_service import UserGetterService
from shared.services.base_service import BaseService


class APIKey(ModelDefinitionMixin, BaseService):

    NEEDS_RELOAD = False

    def __init__(self, username, password, validity):
        user = UserGetterService.get_by_username(username)
        if user and (ENV_VAR == 'DEV' or not user.is_super_admin()) and user.password == encode_password(encode_password(password)):
            self.api_key = generate_jwt_for_user(user, validity)
        else:
            raise Unauthorized

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        return cls(data['username'], data['password'], data.get('validity'))

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            'properties': {
                "username": {
                    "type": "string",
                    "example": "user@domain.com",
                    "description": "The username of the user to get the key for",
                    "value": lambda o: None
                },
                "password": {
                    "type": "string",
                    "example": "mypassword",
                    "description": "The passsword of the user",
                    "value": lambda o: None
                },
                "validity_seconds": {
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "example": 123456,
                    "description": "The number of seconds that the key will be valid for",
                    "default": 3600,
                    "value": lambda o: None
                },
                "api_key": {
                    "type": "string",
                    "description": "The key generated for authenticating API requests",
                    "example": "THE_ACTUAL_KEY",
                    "value": lambda o: o.api_key
                }
            },
            'view_required': ["api_key"],
            'view_allowed': ["api_key"],
            'edit_required': [],
            'edit_allowed': [],
            'create_allowed': ["username", "password", "validity_seconds"],
            'create_required': ["username", "password"]
        }



class APIKeyResource(BaseAPIResourceAll):

    ADD_SERVICE = APIKey
    ADD_PERMISSION = None
    MODEL = APIKey
    VIEW_DOCS_PERMISSION = 'CreateAPITokenAdmin'

    OBJECT_NAME = 'API Key (Login)'
    ADD_DESCRIPTION = 'Used to create API keys from login credentials'
    ADD_SUMMARY = 'CREATE API Key from credentials'
    
    TAG = 'Miscellaneous'

    EXTRA_RESPONSES = {
        'post': {
            401:  {
                "description": "Unauthorized",
                "content": {
                    "application/json": {
                        "schema": API_ERROR_SCHEMA,
                        "example": get_error_example(401, "The server could not verify that you are authorized to access the URL requested. You either supplied the wrong credentials (e.g. a bad password), or your browser doesn't understand how to supply the credentials required.")
                    }
                }
            }
        }
    }
