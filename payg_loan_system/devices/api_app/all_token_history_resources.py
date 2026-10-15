from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from payg_loan_system.devices.services.device_tokens_getter_service import \
    DeviceTokensGetterService
from payg_loan_system.devices.model.token import Token
from constants import BOOLEAN_OPTIONAL_OPTIONS_STRING


class AllDeviceTokensResource(BaseAPIResourceAll):

    LIST_SERVICE = DeviceTokensGetterService
    LIST_PERMISSION = ['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock', 'OrphanedViewStock']
    MODEL = Token
    TAG = 'Devices'
    CUSTOM_ORDER = True

    LIST_VARIABLE = 'uuid'
    LIST_VARIABLE_TYPE = 'string'
    LIST_VARIABLE_FORMAT = 'uuid'
    LIST_VARIABLE_EXAMPLES = ["abdcabcd-1234abcd-1a2b3c4d", "1234abcd-1a2b3c4d-abdcabcd", "1a2b3c4d-abdcabcd-1234abcd"]

    EXTRA_LIST_PARAMS = {
        'serial_number': {
            'in': 'path',
            "name": "serial_number",
            "description": "The serial_number of the device. It must contain the type prefix. ",
            "required": True,
            "example": 'SOL-1234',
            "schema": {
                "type": "string"
            }
        },
        'reverse_order': {
            'in': 'query',
            "name": "reverse_order",
            "description": "To reverse the order of the tokens, putting the most recent first",
            "required": False,
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
            },
            'example': 'true',
            'allowEmptyValue': True,
        },
    }
