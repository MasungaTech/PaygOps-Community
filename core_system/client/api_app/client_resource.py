from flask_restful import request, NotFound
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from core_system.client.services.client_edit_service import ClientEditService
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.users.services.current_user_service import get_current_api_user
from core_system.client.models import Client
from shared.logger.loggers import LogAPI
from shared.logger.loggers import Error
from shared.api_helpers.documented_resource import DocumentedResource, API_ERROR_SCHEMA, get_error_example
from pony import orm

log_api = LogAPI()


class ClientResource(DocumentedResource):

    CLIENTID_PARAM = {
        "name": "id",
        "description": "The unique id of the Client",
        "in": "path",
        "required": True,
        "example": "1234",
        "schema": {
            "type": "integer"
        }
    }

    META = {
        "get": {
            "summary": "Get Client Information",
            "description": "This route is used to get basic data about a client when knowing his/her ID.",
            "tags": ["Clients"],
            "permissions": ['ViewClients'],
            "parameters": [CLIENTID_PARAM],
            "responses": {
                200: {
                    "description": "Returns Client's Information",
                    "content": {
                        "application/json": {
                            "schema": Client.get_model_schema()
                        }
                    }
                },
                404: {
                    "description": "Client Not Found",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(message="Client does not exists or you do not have the permission.")
                        }
                    }
                }
            }
        },
        "post": {
            "summary": "Set Client Information",
            "description": "This route is used to set basic data about a client when knowing his/her ID.",
            "tags": ["Clients"],
            "permissions": ['EditClients'],
            "parameters": [CLIENTID_PARAM],
            "requestBody": {
                "description": "Client Model with ONLY the properties to edit",
                "schema": Client.get_model_schema(op="edit")
            },
            "responses": {
                200: {
                    "description": "Returns Client's Edited Information",
                    "content": {
                        "application/json": {
                            "schema": Client.get_model_schema()
                        }
                    }
                },
                404: {
                    "description": "Client Not Found",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(message="Client does not exists or you do not have the permission.")
                        }
                    }
                },
                400: {
                    "description": "Incorrect Request Data/Format",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example("INVALID_VILLAGE_ID", "Invalid Village ID.")
                        }
                    }
                }
            }
        }
    }

    @verify(**META['get'])
    @orm.db_session
    def get(self, id):
        current_user = get_current_api_user()
        client = ClientGetterService.get_from_user_and_id(current_user, id, strict=True, main_resource=True)
        return client.get_serialized_object(), 200

    @verify(**META['post'], schema=Client.get_model_schema(op="edit", for_validate=True))
    @orm.db_session
    def post(self, id):
        current_user = get_current_api_user()
        client = ClientGetterService.get_from_user_and_id(current_user, id, strict=True, main_resource=True)
        try:
            data = request.json
            ClientEditService.edit_from_data_and_user(client, data, current_user)
            orm.commit()
        except Error as error:
            orm.rollback()
            raise Error(error, code=error.args[0], *error.args[1:])
        except Exception as error:
            orm.rollback()
            raise error
        return client.get_serialized_object(), 200
