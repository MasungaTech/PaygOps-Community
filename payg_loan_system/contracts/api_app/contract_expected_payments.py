


from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.services.contract_expected_payment_service import ExpectedPaymentService
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual


class ContractExpectedPaidResource(BaseAPIResourceIndividual):
    PUBLIC = False # Fix the example if enabling
    GET_SERVICE = ExpectedPaymentService
    GET_PERMISSION = 'ViewClients'
    EDIT_SERVICE = None
    EDIT_PERMISSION = 'ViewClients'
    OBJECT_NAME = 'Contract Expected Payment'
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
