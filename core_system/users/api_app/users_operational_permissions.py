from flask import request
from core_system.users.models.user_model import User
from pony.orm import db_session
from constants import INTEGER_OPTIONAL_OPTIONS_STRING
from core_system.operational_entities.models import UserWithRole
from core_system.users.services.operational_permissions_service import OperationalPermissionsService
from core_system.users.services.user_getter_service import UserGetterService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from core_system.users.services.current_user_service import get_current_api_user
from shared.api_helpers.documented_resource import API_ERROR_SCHEMA, DocumentedResource, get_error_example
from shared.api_helpers.server_helpers.jwt_and_schema_verification import check_permissions, validate_request

class AllOperationalPermissionsResource(BaseAPIResourceAll):

    OBJECT_NAME = 'Operational Permission'

    LIST_SERVICE = OperationalPermissionsService
    ADD_SERVICE = OperationalPermissionsService
    LIST_PERMISSION = 'ViewUsers'
    ADD_PERMISSION = 'EditUsers'
    MODEL = UserWithRole
    TAG = 'Users'
    ENTITY_REQUIRED = False

    EXTRA_LIST_PARAMS = {
        'user_id': {
            'in': 'query',
            "name": "user_id",
            "description": "Filter Operational Permissions by the `user_id` associated",
            "example": 1234,
            "schema": {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING
            }
        },
    }


class CopyOperationalPermissionsResource(DocumentedResource):

    REQUEST_SCHEMA = {
        'type': 'object',
        'properties': {
            'destination_user_id': {
                'type': 'integer',
                "description": "The ID of the user to which the permissions will be copied",
                "example": 123
            }
        },
        'required': ['destination_user_id'],
        'additionalProperties': False
    }

    PERMISSIONS = ['EditUsers']

    @classmethod
    def get_meta(cls):
        return {
            'post': {
                "summary": "COPY Operational Permissions for a user",
                "tags": ["Users"],
                "permissions": cls.PERMISSIONS,
                "parameters": [{
                    "in": "path",
                    "name": "origin_user_id",
                    "description": "The ID of the user to copy permissions from",
                    "required": True,
                    "example": "234",
                    "schema": {
                        "type": "integer",
                    }
                }],
                "requestBody": {
                    "description": "The ID of the user to receive copied permissions",
                    "schema": cls.REQUEST_SCHEMA
                },
                "responses": {
                    200: {
                        "description": "Returns the resulting User's role information",
                        "content": {
                            "application/json": {
                                "schema": User.get_model_schema(),
                                "example": User.get_model_example()
                            }
                        },
                    },
                    404: {
                        "description": "User Not Found",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(message="User Not Found")
                            }
                        },
                    },
                    400: {
                        "description": "Badly formated request",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(code=400, message='You cannot give role Admin in All as it has more permissions than your default role.')
                            }
                        }
                    },
                }
            }
        }

    @db_session
    def post(self, origin_user_id):
        validate_request(self.REQUEST_SCHEMA)
        current_user = get_current_api_user()
        origin_user = UserGetterService.get_from_user_and_id(current_user, origin_user_id, strict=True, main_resource=True)
        destination_user = UserGetterService.get_from_user_and_id(current_user.reload(), request.json.get('destination_user_id'), strict=True)
        check_permissions(permissions=self.PERMISSIONS, person=destination_user.person)
        OperationalPermissionsService.copy_user_permission(current_user, origin_user=origin_user, destination_user=destination_user)
        return destination_user.get_serialized_object()
