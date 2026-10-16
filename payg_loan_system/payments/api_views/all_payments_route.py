from datetime import datetime
from core_system.phone_numbers.services.add_phone_number_service import AddPhoneNumberService
from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from shared.api_helpers.documented_resource import API_ERROR_SCHEMA, DocumentedResource, get_error_example
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.services.add_payment_service import AddPaymentService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from flask_restful import Resource, request
from munch import DefaultMunch
from pony.orm import db_session
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from payg_loan_system.payments.services.payment_router_service import PaymentRouterService
from payg_loan_system.payments.api_views.payment_info_processor import PaymentInfoProcessor
from payg_loan_system.payments.models.wallet import PaymentWallet
from shared.logger.loggers import Error


class AllPaymentsResource(BaseAPIResourceAll):
    LIST_SERVICE = PaymentGetterService
    ADD_SERVICE = AddPaymentService
    LIST_PERMISSION = ['ViewPayments']
    ADD_PERMISSION = ['AddPayments']
    MODEL = Payment
    TAG = 'Payments'
    DEFAULT_PAGE_SIZE = 1000
    LIST_VARIABLE = 'transaction_id'
    LIST_VARIABLE_TYPE = 'string'
    LIST_VARIABLE_EXAMPLES = ['A1234B5678', 'A1234B5679', 'B1234A5678']
    GLOBAL_DB_SESSION = False
    RETRY = 2
    EXTRA_RESPONSES = {
        "post": {
            202: {
                "description": "If the payment was created but could not be processed immediately. This means that any token generation or confirmation SMS might happen later. It can be due to issues with third party services (e.g. Device Cloud not available or SMS service issue). ",
                "content": {
                    "application/json": {
                        "schema": MODEL.get_model_schema() if MODEL else {}
                    }
                }
            },
        }
    }
    EXTRA_LIST_PARAMS = {
        'filter': {
            'in': 'query',
            'name': 'filter',
            'schema': {
                'type': 'string',
                "enum": ['all', 'orphaned'],
            },
            'example': 'all',
            'allowEmptyValue': True,
            'description': 'Allows for filtering just orphaned payments'
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
            'description': 'Allows for filtering payments received after this time'
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
            'description': 'Allows for filtering payments received before this time'
        },
        'source': {
            'in': 'query',
            'name': 'source',
            'schema': {
                'type': 'string',
                "enum": ['cash', 'mobile_money', 'all'],
            },
            'example': 'cash',
            'allowEmptyValue': True,
            'description': 'Allows for filtering payments to show only cash payments, mobile money payments or all of the payments.'
        },
        'wallet_operator': {
            'in': 'query',
            'name': 'wallet_operator',
            'schema': {
                'type': 'string',
            },  
            'example': 'mtn',
            'allowEmptyValue': True,
            'description': 'Allows for filtering payments to show only payments from a specific operator.'
        }
    }

class PaymentsRoutingValidationResource(DocumentedResource):


    @verify(permissions=['AddPayments'], schema=Payment.get_model_schema(op='create', for_validate=True))
    @db_session(retry=2)
    def post(self):
        payment_data = request.json
        data = PaymentInfoProcessor.get_info(payment_data)
        existing_wallet = PaymentWallet.get(FullName=data.get('wallet_name', data.get('sender_name')), operator=data['wallet_operator'])

        # We always use a fake wallet to be able to modify anything that changes due to that payment (e.g. msisdn)
        new_number_str = data.get('wallet_msisdn', data.get('sender_phone_number', data.get('sender_msisdn')))
        if new_number_str:
            try: AddPhoneNumberService._is_phone_number_valid(new_number_str)
            except Error: is_valid = False
            else: is_valid = True
        else:
            is_valid = False

        number = DefaultMunch(number=new_number_str) if is_valid else existing_wallet.phone_number if existing_wallet else None
        
        payment = DefaultMunch(
            PaymentWallet=DefaultMunch(
                FullName=data.get('wallet_name', data.get('sender_name')),
                phone_number=number,
                client=existing_wallet.client if existing_wallet else None,
                lead=existing_wallet.lead if existing_wallet else None,
                user=existing_wallet.user if existing_wallet else None,
            ),
            memo=data.get('memo', data.get('note')),
        )
        destination = PaymentRouterService.find_payment_route(payment)
        data.update({'reconciled': bool(destination)})
        data['destinations'] = []

        destinations = {
            'Lead': ['lead', lambda d: d.future_contract_reference],
            'Contract': ['contract_repayment', lambda d: d.reference],
            'ContractAddOn': ['add_on', lambda d: d.contract.reference],
            'User': ['user', lambda d: d.id]
        }

        if destination:
            info = destinations[destination.__class__.__name__]
            dest = {
                'destination_type': info[0],
                'destination': info[1](destination)
            }
            data.update(dest)
            data['destinations'].append(dest)
        return data

    @classmethod
    def get_meta(cls):
        response_schema = Payment.get_model_schema(include_destination=True)
        response_schema['properties'].update({
            'reconciled': {
                "type": "boolean",
                "description": "Whether the payment was successfully routed to a destination",
                "example": True
            },
        })
        return {
            'post': {
                "tags": ['Payments'],
                "permissions": ['AddPayments'],
                "summary": "VALIDATE Payment Object",
                "description": "You can use this route to validate new incoming payments before sending them into the system, checking if they will be reconciled or not (a recipient is found for that payment). This will NOT create a payment in the system in any case. ",
                "requestBody": {
                    "description": "Payment Model with at least the required properties",
                    "schema": Payment.get_model_schema(op="validate")
                },
                "responses": {
                    200: {
                        "description": "Returns what the payment object will look like and an extra property “reconciled” that will be either true or false depending on whether the payment would have been reconciled or not (i.e. the recipient is found or not) as well as “destination” and “destination_type” if it was routed properly. ",
                        "content": {
                            "application/json": {
                                "schema": response_schema
                            }
                        }
                    },
                    400: {
                        "description": "Incorrect Request Data/Format",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(400, "Invalid amount format.")
                            }
                        }
                    }
                }
            }
        }
