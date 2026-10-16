
from constants import INTEGER_OPTIONAL_OPTIONS_STRING
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.client.models import Client
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll


class ClientsResource(BaseAPIResourceAll):

    MODEL = Client
    TAG = 'Clients'
    LIST_PERMISSION = 'ViewClients'
    LIST_SERVICE = ClientGetterService
    EXTRA_LIST_PARAMS = {
        'search': {
            "in": "query",
            "name": "search",
            'schema': {
                'type': 'string',
            },
            'example': 'Peter',
            'allowEmptyValue': True,
            'description': 'Allows for filtering clients by name'
        },
        'id': {
            "in": "query",
            "name": "id",
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING
            },
            'example': 123,
            'allowEmptyValue': True,
            'description': 'Allows for filtering clients by ID'
        },
        'contract_reference': {
            "in": "query",
            "name": "contract_reference",
            'schema': {
                'type': 'string',
            },
            'example': 'C000001',
            'allowEmptyValue': True,
            'description': 'Allows for filtering clients by contract reference'
        },
        'phone_number': {
            "in": "query",
            "name": "phone_number",
            'schema': {
                'type': 'string',
            },
            'example': '+23454665656',
            'allowEmptyValue': True,
            'description': 'Allows for filtering clients by phone number'
        },
        'client_group_id': {
            'in': 'query',
            'name': 'client_group_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering the client list by the client group of the clients. '
        },
        'serial_number': {
            "in": "query",
            "name": "serial_number",
            'schema': {
                'type': 'string',
            },
            'example': 'NPG-1234',
            'allowEmptyValue': True,
            'description': 'Allows for filtering clients by device serial number'
        },
        'custom_id': {
            "in": "query",
            "name": "custom_id",
            'schema': {
                'type': 'string',
            },
            'example': 'A12345678',
            'allowEmptyValue': True,
            'description': 'Allows to find a client by custom ID'
        },
        'entity_id': {
            'in': 'query',
            'name': 'entity_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering the client list by the operational entity of the clients. You can specify an operational entity of any level and get all the clients included in the sub-levels. '
        },
        'exact_serial_number':{
            "in": "query",
            "name": "exact_serial_number",
            'schema': {
                'type': 'string',
            },
            'example': 'NPG-1234',
            'allowEmptyValue': True,
            'description': 'Allows for searching clients by the exact device serial number'
        }
    }
