from constants import BOOLEAN_OPTIONAL_OPTIONS_STRING, INTEGER_OPTIONAL_OPTIONS_STRING, INTEGER_PATTERN
from messages_system.services.message_service import MessageService
from flask_restful import request
from werkzeug.exceptions import NotFound, Unauthorized, BadRequest
from pony.orm import db_session
from shared.logger.loggers import LogAPI, Error
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify, validate_schema
from core_system.users.services.current_user_service import get_current_api_user
from payg_loan_system.contracts.models.addons_model import AddOnLoanExtensionMode, AddOnType, ContractAddOn
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.addon_list_service import AddonListService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.documented_resource import EMPTY_JSON_ANSWER_SCHEMA, DocumentedResource, API_ERROR_SCHEMA, get_error_example
from shared.services.base_service import BaseService
from datetime import datetime


log_api = LogAPI()


class IndividualAddonResource(DocumentedResource, BaseService):

    MODEL = ContractAddOn
    TAG = 'Add-Ons'
    ALLOWED_API_CALLER = ['patch']
    SUBACTIONS = {
        'patch': {
            'cancel_addons': {
                'name': "Cancel Add-on",
                'description': "Provide a list of add-on references of the add-ons that will be cancelled",
                'permissions': ['CancelAddOns'],
                'properties': ['reference'],
                'presets': {
                    'cancelled': True
                }
            },
            'plan_delivery_date_addons': {
                'name': "Edit Add-on planned delivery date",
                'description': "Edit the planned delivery date for a group of add-ons",
                'permissions': ['ApproveAddOns'],
                'properties': ['reference', 'planned_delivery_date']
            }
        }
    }

    ADDONREF_PARAM = {
        "name": "reference",
        "in": "path",
        "description": "The reference of the Add-On",
        "required": True,
        "example": "C1234001-A0",
        "schema": {
            "type": "string"
        }
    }
    META = {
        "get": {
            "summary": "GET Add-On Object",
            "description": "This route is used to get basic data about an Add-On when knowing the reference.",
            "tags": ["Add-Ons"],
            "permissions": [],
            "parameters": [ADDONREF_PARAM],
            "responses": {
                200: {
                    "description": "Returns Add-On object",
                    "content": {
                        "application/json": {
                            "schema": ContractAddOn.get_model_schema()
                        }
                    }
                },
                404: {
                    "description": "Add-on Not Found",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(message="Add-on does not exists or you do not have the permission.")
                        }
                    }
                }
            }
        },
        "patch": {
            "summary": "EDIT Add-On Object",
            "description": "Allows for editing the properties of an Add-On, including cancelling, approving, etc",
            "tags": ["Add-Ons"],
            "permissions": ['ApproveAddOns'],
            "parameters": [ADDONREF_PARAM],
            "requestBody": {
                "schema": {**{
                    "approved_by": {

                    },
                    "cancelled": {

                    },
                    "time_canceled": {

                    },
                    "cash_collection_agent": {
                    }
                }, **ContractAddOn.get_model_schema(op="edit")},
            },
            "responses": {
                200: {
                    "description": "Edition completed Add-On object",
                    "content": {
                        "application/json": {
                            "schema": ContractAddOn.get_model_schema()
                        }
                    }
                },
                404: {
                    "description": "Add-on Not Found",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(message="Add-on does not exists or you do not have the permission.")
                        }
                    }
                }
            }
        },
        "delete": {
            "summary": "DELETE Add-On Object",
            "description": "This route is used todelete Add-On (only for add-ons on leads)",
            "tags": ["Add-Ons"],
            "permissions": ['ApproveAddOns'],
            "parameters": [ADDONREF_PARAM],
            "responses": {
                204: {
                    "description": "Add-On Deleted",
                    "content": EMPTY_JSON_ANSWER_SCHEMA
                },
                404: {
                    "description": "Add-on Not Found",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(message="Add-on does not exists or you do not have the permission.")
                        }
                    }
                }
            }
        },
    }

    @verify(permissions='ViewAddOns')
    @db_session
    def get(self, reference):
        addon = AddonListService.get_from_user_and_properties(get_current_api_user(), reference=reference, strict=True, main_resource=True)
        return addon.get_serialized_object()
    
    @classmethod
    def patch_core(cls, reference, user, data):
        addon = AddonListService.get_from_user_and_properties(user, reference=reference, strict=True, main_resource=True)
        answer = AddonService.edit_from_data_and_user(addon, data, user)
        if answer and isinstance(answer, dict) and not answer['success']:
            raise Error(answer)
        return AddonListService.get_from_user_and_properties(user, reference=reference)
        

    @verify(permissions=['ApproveAddOns'], schema=ContractAddOn.get_model_schema(op="edit", for_validate=True))
    @db_session
    def patch(self, reference):
        addon = self.patch_core(reference, get_current_api_user(), request.json)
        return addon.get_serialized_object() if addon else {}

    @verify(permissions=['ApproveAddOns'])
    @db_session
    def delete(self, reference):
        addon = AddonListService.get_from_user_and_properties(get_current_api_user(), reference=reference, strict=True, main_resource=True)
        AddonService.delete_from_object_and_user(addon, get_current_api_user())
        return '', 204

class AllAddonsResource(BaseAPIResourceAll):

    LIST_SERVICE = AddonListService
    ADD_SERVICE = AddonService
    ALLOWED_API_CALLER = ['post']
    LIST_PERMISSION = 'ViewAddOns'
    ADD_PERMISSION = 'AddAddOns'

    MODEL = ContractAddOn
    TAG = 'Add-Ons'

    LIST_VARIABLE = 'reference'
    LIST_VARIABLE_TYPE = 'string'
    LIST_VARIABLE_EXAMPLES = ['C1234001-A0', 'C1234001-A1', 'C1256001-A0']

    EXTRA_LIST_PARAMS = {
        'offer_id': {
            'in': 'query',
            'name': 'offer_id',
            'schema': {
                "oneOf": [
                    {"type": "string", "pattern": INTEGER_PATTERN},
                    {"type": "array", "items": {"type": "integer"}},
                    {"type": "array", "items": {"type": "string", "pattern": INTEGER_PATTERN}},
                ]
            },
            'example': [12, 13],
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by their add-on offer ID (single value or list).'
        },
        'offer_version_id': {
            'in': 'query',
            'name': 'offer_version_id',
            'schema': {
                "oneOf": [
                    {"type": "string", "pattern": INTEGER_PATTERN},
                    {"type": "array", "items": {"type": "integer"}},
                    {"type": "array", "items": {"type": "string", "pattern": INTEGER_PATTERN}},
                ]
            },
            'example': [24, 25],
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by their add-on offer version ID (single value or list).'
        },
        'offer_code': {
            'in': 'query',
            'name': 'offer_code',
            'schema': {
                'type': 'string',
            },
            'example': 'OFFER_1',
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by the add-on offer code.'
        },
        'offer_name': {
            'in': 'query',
            'name': 'offer_name',
            'schema': {
                'type': 'string',
            },
            'example': 'Extra Panel',
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by add-on offer name (case-insensitive contains).'
        },
        'loan_mode': {
            'in': 'query',
            'name': 'loan_mode',
            'schema': {
                'type': 'string',
                'enum': AddOnLoanExtensionMode.to_list(),
            },
            'example': AddOnLoanExtensionMode.duration,
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by loan mode.'
        },
        'type': {
            'in': 'query',
            'name': 'type',
            'schema': {
                'type': 'string',
                'enum': AddOnType.to_list(),
            },
            'example': AddOnType.lump_sum,
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by add-on type.'
        },
        'approved': {
            'in': 'query',
            'name': 'approved',
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
            },
            'example': 'false',
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by approval state. `true` means approved (not pending); `false` means pending.'
        },
        'delivered': {
            'in': 'query',
            'name': 'delivered',
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
            },
            'example': 'false',
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by delivered status.'
        },
        'cancelled': {
            'in': 'query',
            'name': 'cancelled',
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
            },
            'example': 'false',
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by cancelled status.'
        },
        'paid': {
            'in': 'query',
            'name': 'paid',
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
            },
            'example': 'false',
            'allowEmptyValue': True,
            'description': 'Allows for filtering add-ons by paid status.'
        },
        'lead_id': {
            'in': 'query',
            'name': 'lead_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering addons by their lead\'s ID'
        },
        'contract_reference': {
            'in': 'query',
            'name': 'contract_reference',
            'schema': {
                'type': 'string',
            },
            'example': 'C0121234',
            'allowEmptyValue': True,
            'description': 'Allows for filtering addons by their contract\'s reference'
        },
        'planned_delivery_date_from': {
            'in': 'query',
            'name': 'planned_delivery_date_from',
            'schema': {
                'type': 'string',
                'format': 'date',
            },
            'example': datetime.now().isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering addons by their planned delivery date after this time'
        },
        'planned_delivery_date_to':{
            'in': 'query',
            'name': 'planned_delivery_date_to',
            'schema': {
                'type': 'string',
                'format': 'date',
            },
           'example': datetime.now().isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering addons by their planned delivery date before this time'
        }
    }

    @classmethod
    def _get_default_name(cls):
        return "Add-Ons"

    @verify(permissions=['ApproveAddOns'])
    @db_session
    def patch(self):
        addons_data = request.json
        user = get_current_api_user()
        schema=ContractAddOn.get_model_schema(op="edit", for_validate=True)
        edited_ids = []
        for addon_data in addons_data:
            addon = AddonListService.get_from_user_and_id(user, addon_data['id'])
            if not addon:
                raise NotFound(f'Add-on [{addon_data["id"]}] was not found')
            edited_ids.append(addon_data.pop('id'))
            validate_schema(addon_data, schema)
            answer = AddonService.edit_from_data_and_user(addon, addon_data, user)
            if answer and isinstance(answer, dict) and not answer['success']:
                raise Error(MessageService.get_message(answer))
        return {
            'success': True,
            'message': 'The following addons were edited successfully: '+str(edited_ids)
        }, 200
    
    @classmethod
    def get_meta_patch(cls):
        return {
            "permissions": ["ApproveAddOns"],
            "tags": ["Add-Ons"],
            "responses": {
                200: {
                    "description": "Edited successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "success": {
                                        "description": "Flag indicating the result of the operation",
                                        "type": "boolean",
                                        "example": "true"
                                    },
                                    "message": {
                                        "description": "Description of result",
                                        "type": "string",
                                        "example": "The following addons were edited successfully: [1, 2, 3]"
                                    },
                                }
                            },
                            "example": {
                                'success': True,
                                'message': 'The following addons were edited successfully: [1, 2, 3]'
                            }
                        }
                    }
                },
                400: {
                    "description": "Edited successfully",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(401, "The server could not verify that you are authorized to access the URL requested. You either supplied the wrong credentials (e.g. a bad password), or your browser doesn't understand how to supply the credentials required.")
                        }
                    }
                }
            }
        }
