from constants import PHONE_PATTERN
from datetime import datetime
from payg_loan_system.reversed_payments.domain import PaymentReversal
from shared.api_helpers.documented_resource import API_ERROR_SCHEMA, DocumentedResource, get_error_example
from flask_restful import request
from pony.orm import db_session
from shared.logger.loggers import LogAPI, Error
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from shared.services.settings_service import SettingsService
from payg_loan_system.reversed_payments.services.service import PaymentReversalService
from payg_loan_system.reversed_payments.services.validator import PaymentReversalValidator
from core_system.users.services.current_user_service import get_current_api_user

log_api = LogAPI()

# Amount can be number of string for retrocompatibility
REVERSED_PAYMENT_SCHEMA = {
    "properties": {
        "reference": {
            "type": "string",
            "description": "See `reversal_transaction_id`",
            "deprecated": True
        },
        "reversal_transaction_id": {
            "description": "The unique id of the reversal transaction",
            "example": "REV-23444545",
            "type": "string"
        },
        "payment_reference": {
            "description": "See `payment_transaction_id`",
            "deprecated": True,
            "type": "string"
        },
        "payment_transaction_id": {
            "description": "The unique id of the payment that is being reversed",
            "example": "TX-23444545",
            "type": "string"
        },
        "sent_datetime": {
            "description": "The datetime at which the reversal was sent",
            "example": datetime.now().isoformat(),
            "oneOf": [
                {
                    "type": "string",
                    "format": "date-time",
                },
                {
                    "type": "null",
                }
            ]
        },
        "sender_name": {
            "type": "string",
            "description": "The sender name",
            "example": "Client Name",
        },
        "wallet_name": {
            "type": "string",
            "description": "The mobile money wallet unique name",
            "example": "Wallet 1",
        },
        "sender_msisdn": {
            "description": "The phone number of the sender",
            "example": "+245645645656",
            "oneOf": [
                {
                    "type": "string",
                    "pattern": PHONE_PATTERN,
                },
                {
                    "type": "null",
                },
                { "type": "string", "maxLength": 0}
            ]
        },
        "wallet_msisdn": {
            "description": "The phone number of the mobile money wallet",
            "example": "+245645645656",
            "oneOf": [
                {
                    "type": "string",
                    "pattern": PHONE_PATTERN,
                },
                {
                    "type": "null",
                },
                { "type": "string", "maxLength": 0}
            ]
        },
        "wallet_operator": {
            "description": "The mobile money operator",
            "example": "MTN",
            "type": "string"
        }
    },
    "allOf": [
        {
            "oneOf": [
                {"required": ["payment_reference"]},
                {"required": ["payment_transaction_id"]}
            ],
        },
    ],
}


class PaymentReversalResource(DocumentedResource):

    ALLOWED_API_CALLER = ['post']

    META = {
        "post": {
            "summary": "Create Payment Reversal",
            "description": "Create a new payment reversal.",
            "tags": ["Payments"],
            "permissions": ['AddReversedPayments'],
            "requestBody": {
                "schema": {
                    "properties": REVERSED_PAYMENT_SCHEMA["properties"],
                    "required": ["payment_transaction_id", "reversal_transaction_id"],
                    "aditionalProperties": False
                }
            },
            "responses": {
                200: {
                    "description": "Payment reversal already exists",
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "success": {
                                        "description": "Flag indicating if the opearation was successful",
                                        "type": "boolean"
                                    },
                                    "warning": {
                                        "description": "Text informing of any warning",
                                        "type": "string"
                                    }
                                }
                            },
                            "example": {
                                "success": True,
                                "warning": "The reversal transaction already exists in the system."
                            }
                        }
                    }
                },
                201: {
                    "description": "Payment reversal created correctly",
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "success": {
                                        "description": "Flag indicating if the opearation was successful",
                                        "type": "boolean"
                                    }
                                }
                            },
                            "example": {
                                "success": True,
                            }
                        }
                    }
                },
                400: {
                    "description": "Badly formated request",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(code=400, message='Invalid format')
                        }
                    }
                },
            }
        }
    }

    @classmethod
    def post_core(cls, data, user):
        manual_action = data.get('manual_action', False) in [True, 'true']

        # validation
        PaymentReversal.deserialize(data)

        reversal, code = PaymentReversalService.process(data)

        if reversal.payment and user.can_access('HandleReversedPayments'):
            if SettingsService.get_setting('AutomaticPaymentReversal') or manual_action:
                try:
                    PaymentReversalService.reverse_reversal(reversal, user)
                except Error:
                    pass
        response = {'success': True}
        if code == 200:
            response.update({'warning': 'The reversal transaction already exists in the system.'})
        return response, code

    @verify(permissions=['AddReversedPayments'], schema=REVERSED_PAYMENT_SCHEMA)
    @db_session
    def post(self):
        data = request.json
        user = get_current_api_user()
        return self.post_core(data, user)