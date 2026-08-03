from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from payg_loan_system.payments.models.payment import Payment

class GetPaymentResource(BaseAPIResourceIndividual):

    GET_SERVICE = PaymentGetterService
    GET_PERMISSION = ['AddPayments']
    OBJECT_NAME = 'Payment'
    MODEL = Payment
    TAG = 'Payments'
    ID_PARAM = {
        "name": "transaction_id",
        "in": "path",
        "description": "The Transaction Id of the payment",
        "example": "TransactionID1234",
        "property": "Reference",
        "required": True,
        "schema": Payment.get_model_schema()['properties']['transaction_id']
    }
    EXTRA_PARAMS = {
        'wallet_operator': {
            'in': 'query',
            'name': 'wallet_operator',
            'schema': {
                'type': 'string',
            },
            'example': 'mpesa',
            'allowEmptyValue': False,
            'description': 'Allows for filtering payments to show only payments from different wallet operators.'
        }
    }
    MULTIPLE_OBJECTS_FOUND_ERROR = 'Multiple {OBJECT_NAME}s found with the same reference, please provide a wallet operator.'