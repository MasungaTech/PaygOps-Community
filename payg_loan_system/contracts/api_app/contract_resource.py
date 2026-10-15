from core_system.portfolios.model import PortfolioEntity
from payg_loan_system.contracts.models.contract_status import ContractStatus
from shared.api_helpers.server_helpers.jwt_and_schema_verification import check_permissions
from werkzeug.exceptions import BadRequest, NotFound
from core_system.users.services.current_user_service import get_current_api_user
from datetime import datetime, timedelta
from shared.api_helpers.query_parameters_validator import QueryParametersValidator
import pytz
from flask import request
from shared.api_helpers.documented_resource import API_ERROR_SCHEMA, DocumentedResource, get_error_example
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from payg_loan_system.contracts.models.contract_model import Contract
from pony import orm
from constants import BOOLEAN_OPTIONAL_OPTIONS_STRING, INTEGER_OPTIONAL_OPTIONS_STRING
from shared.services.base_service import BaseService


class ContractEditService(BaseService):

    @classmethod
    def _edit_from_data_and_user(cls, this_object, data, user):
        user.check_access('EditPortfolioClients', person=this_object.client.person)
        if 'portfolio_id' in data:
            portfolio = PortfolioEntity.get(id=data['portfolio_id'])
            if not portfolio and data['portfolio_id']:
                raise BadRequest('Portfolio id not valid')
            this_object.portfolio = portfolio


class IndividualContractResource(BaseAPIResourceIndividual):
    GET_SERVICE = ContractGetterService
    GET_PERMISSION = 'ViewClients'
    EDIT_SERVICE = ContractEditService
    EDIT_PERMISSION = 'EditPortfolioClients'
    OBJECT_NAME = 'Contract'
    MODEL = Contract
    TAG = 'Contracts'
    ID_PARAM = {
        "name": "contract_reference",
        "property": "reference",
        "description": "The reference of the Contract",
        "in": "path",
        "required": True,
        "example": "C1234001",
        "schema": {
            "type": "string"
        }
    }
    ALLOWED_API_CALLER = ['post']

    @classmethod
    def _get_relevant_person(cls, this_object):
        return this_object.client.person


class ContractHistoryResource(DocumentedResource):

    PERMISSION = 'ViewClients'
    PARAMETERS = [{
        "name": "contract_reference",
        "description": "The contract reference to get the history for",
        "property": "reference",
        "schema": {
            "type": "string",
        },
        "required": True,
        "in": "path",
        "example": "C1234001"
    },{
        "name": "times",
        "in": "query",
        "description": "Date-time points at which the metrics should be calculated, as comma separated values",
        "required": True,
        "schema": {
            "type": "array",
            "items": {
                "type": "string",
                "format": "date-time",
            }
        },
        "examples": {
            'single': {
                "value": datetime.now().isoformat(),
                "summary": "One single point in time"
            },
            'several': {
                "value": (datetime.now()-timedelta(days=30)).isoformat()+','+datetime.now().isoformat(),
                "summary": "Calculated 30 days ago and now"
            },
            'with_timezone': {
                "value": (datetime.now(tz=pytz.timezone("Africa/Windhoek"))).isoformat(),
                "summary": "Times with timezones"
            }
        },
    }]

    EXAMPLES = {
        key: {
            "summary": example['summary'],
            "value": [Contract.get_model_example(
                include_objects=True,
                special_data=True
            )]*len(example['value'].split(','))
        } for key, example in PARAMETERS[1]['examples'].items()
    }

    META = {
        'get': {
            "tags": ["Contracts"],
            "permissions": [PERMISSION],
            "summary": "GET Contract History",
            "parameters": PARAMETERS,
            "responses": {
                200: {
                    "description": "Returns list with Contract's Information at the different times",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": Contract.get_model_schema(include_objects=True, special_data=True)['properties']
                                }
                            },
                            "examples": EXAMPLES
                        }
                    }
                },
                404: {
                    "description": "Contract Not Found",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(message="Contract Not Found")
                        }
                    },
                },
                400: {
                    "description": "Incorrect Request Data/Format",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(400, "Invalid Id format.")
                        }
                    }
                }
            }
        }
    }

    @orm.db_session
    def get(self, contract_reference):
        user = get_current_api_user()
        contract = ContractGetterService.get_from_user_and_properties(user, reference=contract_reference, strict=True, main_resource=True)
        check_permissions(permissions=self.PERMISSION, person=contract.client.person)
        times = QueryParametersValidator.validate_and_decode(request.args, self.PARAMETERS)['times']        
        return [contract.get_serialized_object(include_objects=True, special_data=True, at_time=time) for time in times]


class ContractsResource(BaseAPIResourceAll):

    MODEL = Contract
    TAG = 'Contracts'
    LIST_PERMISSION = 'ViewClients'
    LIST_SERVICE = ContractGetterService

    LIST_VARIABLE = 'reference'
    LIST_VARIABLE_TYPE = 'string'
    LIST_VARIABLE_FORMAT = ''
    LIST_VARIABLE_EXAMPLES = ["C00112233", "C44112233", "C55112233"]

    EXTRA_LIST_PARAMS = {
        'special_data': {
            "name": "special_data",
            "in": "query",
            "description": "Include additional metrics. ",
            "required": False,
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
            },
            "examples": {
                'true': {
                    "value": "true",
                    "summary": "With additional metrics"
                },
                'false': {
                    "value": "false",
                    "summary": "Without additional metrics"
                }
            }
        },
        'entity_id': {
            'in': 'query',
            'name': 'entity_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering the contract list by the operational entity of the contracts. You can specify an operational entity of any level and get all the contracts included in the sub-levels. '
        },
        'client_group_id': {
            'in': 'query',
            'name': 'client_group_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering the contract list by the client group. '
        },
        'client_id': {
            'in': 'query',
            'name': 'client_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering the contract list by the client id. '
        },
        'status': {
            'in': 'query',
            'name': 'status',
            'schema': {
                "enum": ContractStatus.to_list()
            },
            "example": ContractStatus.to_list()[0],
            'allowEmptyValue': True,
            'description': 'Allows for filtering the contract list by status. '
        },
        'from_date': {
            'in': 'query',
            'name': 'from_date',
            'schema': {
                'type': 'string',
                'format': 'date-time'
            },
            'example': datetime.now().isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering contracts created after that date'
        },
        'to_date': {
            'in': 'query',
            'name': 'to_date',
            'schema': {
                'type': 'string',
                'format': 'date-time'
            },
            'example': datetime.now().isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering contracts created before that date'
        },
        'min_payment_due': {
            'in': 'query',
            'name': 'min_days_before_due',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': 2,
            'allowEmptyValue': True,
            'description': 'Allows for filtering contracts with payment due after that date'
        },
        'max_payment_due': {
            'in': 'query',
            'name': 'max_days_before_due',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': 3,
            'allowEmptyValue': True,
            'description': 'Allows for filtering contracts with payment due before that date'
        },
        'delivery_status': {
            'in': 'query',
            'name': 'delivery_status',
            'schema': {
                'type': 'string',
                'enum': ['all', 'delivered', 'partially_delivered']
            },
            'example': 'delivered',
            'allowEmptyValue': True,
            'description': 'Allows for filtering contracts by add-on delivery status'
        },
        
    }