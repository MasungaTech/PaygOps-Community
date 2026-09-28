from werkzeug.exceptions import Unauthorized

from constants import FLOAT_OPTIONAL_OPTIONS
from core_system.users.models.user_model import User
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.documented_resource import (API_ERROR_SCHEMA,
                                                    get_error_example)
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt
from core_system.role.methods.getters import get_authorized_pages_from_role_id
from core_system.role.services import PermissionService
from datetime import datetime, timedelta
import config
from shared.logger.loggers import Error
from shared.services.base_service import BaseService


class ThirdPartyAPIKey(ModelDefinitionMixin, BaseService):

    NEEDS_RELOAD = False

    def __init__(self, user_id, validity, generating_user):
        user = User.get(id=user_id)
        if not user:
            raise Error('User not found', code="USER_NOT_FOUND_ERROR")
        token_expiry = int(validity)
        token_expiry_datetime = datetime.now() + timedelta(seconds=token_expiry)
        new_role = user.AuthorizationLevel
        if PermissionService.allowed_to_change_to_role(generating_user, new_role):
            permissions = get_authorized_pages_from_role_id(new_role.id)
            this_token = generate_jwt(user.id, permissions, 'Solaris Offgrid', config.api_secret, token_expiry_datetime)
            self.api_key = str(this_token)
        else:
            raise Error('You do not have the proper permissions to create an API key for this user.')

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        return cls(data['user_id'], data.get('validity_seconds') or 3600, user)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            'properties': {
                "user_id": {
                    "type": "string",
                    "example": "123",
                    "description": "The user_id of the user to get the API key for",
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
            'create_allowed': ["user_id", "validity_seconds"],
            'create_required': ["user_id"]
        }



class ThirdPartyAPIKeyResource(BaseAPIResourceAll):

    ADD_SERVICE = ThirdPartyAPIKey
    ADD_PERMISSION = 'CreateAPITokenAdmin'
    MODEL = ThirdPartyAPIKey

    OBJECT_NAME = 'Third Party API Key'
    ADD_DESCRIPTION = 'Used to create API keys that belongs to arbitrary users'
    ADD_SUMMARY = 'CREATE API Key for any User'

    TAG = 'Miscellaneous'
