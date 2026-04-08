from flask import request
from pony.orm import db_session
from core_system.client.models import Client
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.client.services.client_merger_service import ClientMergerService
from core_system.users.services.current_user_service import get_current_api_user
from shared.api_helpers.documented_resource import API_ERROR_SCHEMA, DocumentedResource, get_error_example
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify


PERMISSION = 'MergeClients'
SCHEMA = {
    'type': 'object',
    'properties': {
        'target_client_id': {
            'type': 'integer',
            'description': "The ID of the client to be merged with",
            "example": "123"
        }
    },
    'required': ['target_client_id'],
    'additionalProperties': False
}

class MergeClientsResource(DocumentedResource):

    @classmethod
    def get_meta(cls):
        return {
            'post': {
                "permissions": PERMISSION,
                "summary": "MERGE Clients",
                "parameters": [{
                    "in": "path",
                    "name": "original_client_id",
                    "description": "The ID of the original client to merge with",
                    "required": True,
                    "example": "234",
                    "schema": {
                        "type": "integer",
                    }
                }],
                "requestBody": {
                    "description": "The ID of the target client to be merged with the original client",
                    "schema": SCHEMA
                },
                "responses": {
                    200: {
                        "description": "Returns the resulting Client's information",
                        "content": {
                            "application/json": {
                                "schema": Client.get_model_schema(),
                                "example": Client.get_model_example()
                            }
                        },
                    },
                    404: {
                        "description": "Client Not Found",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(message="Client Not Found")
                            }
                        },
                    },
                    400: {
                        "description": "Badly formated request",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(code=400, message='Target client ID is required')
                            }
                        }
                    },
                }
            }
        }

    @verify(permissions=[PERMISSION], schema=SCHEMA)
    @db_session
    def post(self, original_client_id):
        user = get_current_api_user()
        original_client = ClientGetterService.get_from_user_and_id(user, original_client_id, strict=True, main_resource=True)
        target_client = ClientGetterService.extract_from_user_and_id(user, request.json, 'target_client_id', strict=True, empty_allowed=False)
        ClientMergerService.merge(original_client, target_client)
        return original_client.get_serialized_object(), 200
