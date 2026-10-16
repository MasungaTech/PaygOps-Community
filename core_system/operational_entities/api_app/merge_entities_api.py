from flask import request
from werkzeug.exceptions import NotFound
from pony.orm import db_session
from core_system.operational_entities.models import HierarchicalOperationalEntity
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.operational_entities.services.operational_entity_merger_service import OperationalEntityMerger
from core_system.users.services.current_user_service import get_current_api_user
from shared.api_helpers.documented_resource import API_ERROR_SCHEMA, DocumentedResource, get_error_example
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify


PERMISSION = 'ConfigureOperationalEntitiesAdmin'
SCHEMA = {
    'type': 'object',
    'properties': {
        'origin_entity_id': {
            'type': 'integer',
            'description': "The ID of the entity that will be merged into the other",
            "example": "123"
        }
    },
    'required': ['origin_entity_id'],
    'additionalProperties': False
}

class MergeOperationalEntitiesResource(DocumentedResource):

    @classmethod
    def get_meta(cls):
        return {
            'post': {
                "tags": ['Locations'],
                "permissions": PERMISSION,
                "summary": "MERGE Operational Entities",
                "parameters": [{
                    "in": "path",
                    "name": "target_entity_id",
                    "description": "The ID of the target entity to merge into",
                    "required": True,
                    "example": "234",
                    "schema": {
                        "type": "integer",
                    }
                }],
                "requestBody": {
                    "description": "The ID of the origin entitiy to be merged into the target entity",
                    "schema": SCHEMA
                },
                "responses": {
                    200: {
                        "description": "Returns the resulting Entity's information",
                        "content": {
                            "application/json": {
                                "schema": HierarchicalOperationalEntity.get_model_schema(),
                                "example": HierarchicalOperationalEntity.get_model_example()
                            }
                        },
                    },
                    404: {
                        "description": "Operational Entity Not Found",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(message="Operational Entity Not Found")
                            }
                        },
                    },
                    400: {
                        "description": "Badly formated request",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(code=400, message='Operational Entites must have same level')
                            }
                        }
                    },
                }
            }
        }

    @verify(permissions=[PERMISSION], schema=SCHEMA)
    @db_session
    def post(self, target_entity_id):
        user = get_current_api_user()
        target_entity = OperationalEntitiesGetterService.get_from_user_and_id(user, target_entity_id, strict=True, main_resource=True)
        origin_entity = OperationalEntitiesGetterService.extract_from_user_and_id(user, request.json, 'origin_entity_id', strict=True, empty_allowed=False)
        OperationalEntityMerger.merge(origin_entity, target_entity)
        return target_entity.get_serialized_object(model=HierarchicalOperationalEntity)
