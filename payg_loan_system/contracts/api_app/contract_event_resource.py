from constants import INTEGER_OPTIONAL_OPTIONS_STRING
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from payg_loan_system.contracts.models.contract_event_model import ContractEvent, ContractEventType
from payg_loan_system.contracts.services.contract_event_list_service import ContractEventListService
from datetime import datetime


class AllContractEventResource(BaseAPIResourceAll):
    LIST_SERVICE = ContractEventListService
    LIST_PERMISSION = 'ViewClients'
    MODEL = ContractEvent
    TAG = 'Contracts'
    OBJECT_NAME = 'Events'

    EXTRA_LIST_PARAMS = {
        'client_id': {
            'in': 'query',
            'name': 'client_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering events for a specific client by id'
        },
        'contract_reference': {
            'in': 'query',
            'name': 'contract_reference',
            'schema': {
                'type': 'string',
            },
            'example': 'C0121234',
            'allowEmptyValue': True,
            'description': 'Allows for filtering events for a specific contract by its contract reference'
        },
        'event_type': {
            'in': 'query',
            'name': 'event_type',
            'schema': {
                'type': 'string',
                'enum': ContractEventType.to_list()
            },
            'example': 'Creation',
            'allowEmptyValue': True,
            'description': 'Allows for filtering the events by type. '
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
            'description': 'Allows for filtering events done after this time'
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
            'description': 'Allows for filtering events done before this time'
        },
    }


class IndividualContractEventResource(BaseAPIResourceIndividual):
    GET_SERVICE = ContractEventListService
    GET_PERMISSION = 'ViewClients'
    OBJECT_NAME = 'Events'
    MODEL = ContractEvent
    TAG = 'Contracts'