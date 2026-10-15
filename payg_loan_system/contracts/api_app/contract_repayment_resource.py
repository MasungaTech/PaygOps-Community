from constants import BOOLEAN_OPTIONAL_OPTIONS_STRING, INTEGER_OPTIONAL_OPTIONS_STRING
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.services.contract_repayment_list_service import ContractRepaymentListService
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from datetime import datetime


class AllContractRepaymentResource(BaseAPIResourceAll):
    LIST_SERVICE = ContractRepaymentListService
    LIST_PERMISSION = 'ViewClients'
    MODEL = ContractRepayment
    TAG = 'Contracts'
    OBJECT_NAME = 'Repayments'
    CUSTOM_ORDER = True

    EXTRA_LIST_PARAMS = {
        'client_id': {
            'in': 'query',
            'name': 'client_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows for filtering repayment for a specific client by id'
        },
        'contract_reference': {
            'in': 'query',
            'name': 'contract_reference',
            'schema': {
                'type': 'string',
            },
            'example': 'C0121234',
            'allowEmptyValue': True,
            'description': 'Allows for filtering repayments for a specific contract by its contract reference'
        },
        'repayment_type': {
            'in': 'query',
            'name': 'repayment_type',
            'schema': {
                'type': 'string',
                'enum': ContractRepaymentDiscountTypes.to_list() + ['Contract Payment']
            },
            'example': 'Downpayment',
            'allowEmptyValue': True,
            'description': 'Allows for filtering the repayments by type. '
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
            'description': 'Allows for filtering repayments done after this time'
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
            'description': 'Allows for filtering repayments done before this time'
        },
        'include_reversed': {
            'in': 'query',
            'name': 'include_reversed',
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
                'default': False,
            },
            'example': False,
            'default': False,
            'allowEmptyValue': True,
            'description': 'Allows showing reversed contract payments (one item for the contract payment and another for the reversal)'
        },
        'reverse_order': {
            'in': 'query',
            "name": "reverse_order",
            "description": "To reverse the order of the contract payments, putting the most recent first",
            "required": False,
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING,
            },
            'example': 'true',
            'allowEmptyValue': True,
        },
    }


class IndividualContractRepaymentResource(BaseAPIResourceIndividual):
    GET_SERVICE = ContractRepaymentListService
    GET_PERMISSION = 'ViewClients'
    OBJECT_NAME = 'Repayments'
    MODEL = ContractRepayment
    TAG = 'Contracts'

    @classmethod
    def _get_relevant_entity(cls, this_object):
        return this_object.contract.client.person.village