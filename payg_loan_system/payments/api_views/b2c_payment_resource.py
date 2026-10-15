
from datetime import datetime
from pony.orm import db_session
from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from payg_loan_system.payments.services.b2c_payment_service import B2CPaymentService
from payg_loan_system.payments.models.payment import Payment

class IndividualB2CPaymentResource(BaseAPIResourceIndividual):
    GET_SERVICE = PaymentGetterService
    GET_PERMISSION = ['AddPayments']
    EDIT_SERVICE = B2CPaymentService
    EDIT_PERMISSION = ['AddPayments']
    MODEL = Payment
    TAG = 'Payments'
    OBJECT_NAME = 'B2C Payment'
    ALTERNATE_MODEL_DEFINITION = 'b2c_payment'
    ID_PARAM = {
        "name": "payment_uuid",
        "in": "path",
        "description": "The UUID of the payment",
        "example": "123e4567-e89b-12d3-a456-426614174000",
        'allowEmptyValue': True,
        "schema": {
            "type": "string"
        }
    }

class AllB2CPaymentResource(BaseAPIResourceAll):
    #ADD_SERVICE = B2CPaymentService # This is ONLY for testing purposes
    #ADD_PERMISSION = ['SuperAdmin']
    LIST_PERMISSION = ['AddPayments']
    LIST_SERVICE = B2CPaymentService
    MODEL = Payment
    TAG = 'Payments'
    OBJECT_NAME = 'B2C Payment'
    ALTERNATE_MODEL_DEFINITION = 'b2c_payment'
