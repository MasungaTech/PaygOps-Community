from datetime import datetime
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.contracts.services.addon_list_service import AddonListService
from constants import BOOLEAN_OPTIONAL_OPTIONS_STRING, FLOAT_OPTIONAL_OPTIONS, INTEGER_OPTIONAL_OPTIONS, INTEGER_OPTIONAL_OPTIONS_STRING, OPTIONAL_STRING_OPTIONS
from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from payg_loan_system.payments.services.wallet_getter_service import WalletGetterService
from shared.api_helpers.documented_resource import API_ERROR_SCHEMA, get_error_example
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from payg_loan_system.payments.services.payment_router_service import PaymentRouterService
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService
from payg_loan_system.contracts.models.reconciled_payment_model import ReconciledPayment
from decimal import Decimal, InvalidOperation
from messages_system.services.message_service import MessageService
from flask_restful import request
from pony.orm import db_session
from pony.orm.core import MultipleObjectsFoundError
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from shared.logger.loggers import LogAPI, Error
from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from core_system.users.services.current_user_service import get_current_api_user


log_api = LogAPI()

reconcile_payment_schema = {
    "properties": {
        "source": {
            "type": "string",
            "description": "Whether the source of the money is a wallet's balance or an specific payment. If `payment` chosen, `payment_reference` is required. If `balance`, then `account_id` and `amount` are required",
            "enum": ["payment", "balance"]
        },
        "payment_reference": {
            "oneOf": [
                {
                    "type": "string"
                },
                {
                    "type": "null"
                }
            ],
            "example": "PAY-1234",
            "description": "The reference (transaction_id) of the payment that is going to be reconciled"
        },
        "amount": {
            "oneOf": FLOAT_OPTIONAL_OPTIONS,
            "example": 12.34,
            "description": "The amount to be taken from the wallet to be reconciled",
        },
        "amount_to_add": {
            "type": "number",
            "format": "float",
            "example": "20.43",
            "description": "This amount can be positive or negative. If positive, amount is added to the wallet, if negative amount is deducted from the wallet"
        },
        "account_id": {
            "oneOf": INTEGER_OPTIONAL_OPTIONS,
            "example": 123,
            "description": "The ID of the wallet (account) from which the money is going to be reconciled",
        },
        "destination": {
            "type": "string",
            "enum": ["contract", "lead", "addon", "user", "auto", "adjustment"],
            "description": "The type of destination of the money, depending on the type an extra property indicating the actual destination is required. If auto is selected (only for payments), the payment is routed according to the payment router options"
        },
        "note": {
            "oneOf": OPTIONAL_STRING_OPTIONS,
            "example": "This is a note",
            "description": "A note you can add to explain an adjustment (only works if destination is 'adjustment')."
        },
        "contract_reference": {
            "oneOf": [
                {
                    "type": "string"
                },
                {
                    "type": "null"
                }
            ],
            "example": "C0123243",
            "description": "The reference of the contract to which the money is going to be reconciled"
        },
        "lead_id": {
            "oneOf": INTEGER_OPTIONAL_OPTIONS,
            "example": 123,
            "description": "The ID of the lead to which the money is going to be reconciled",
        },
        "addon_reference": {
            "oneOf": [
                {
                    "type": "string"
                },
                {
                    "type": "null"
                }
            ],
            "example": "C0123243-A1",
            "description": "The reference of the add-on to which the money is going to be reconciled"
        },
        "user_id": {
            "oneOf": INTEGER_OPTIONAL_OPTIONS,
            "example": 123,
            "description": "The ID of the user to which the money is going to be reconciled (this effectively reduces the cash in the user wallets), used when a user transfers cash collected to the company",
        },
        'wallet_operator': {
            "type": "string",
            "example": "mpesa",
            'description': 'The operator of the wallet from which the money is going to be reconciled.'
        }
    },
    "required": ["destination", "source"]
}

class IndividualReconciledPaymentResource(BaseAPIResourceIndividual):
    GET_SERVICE = ReconciledPaymentService
    GET_PERMISSION = 'ViewPayments'
    GET_GLOBAL_PERMISSION = 'ViewPayments'
    DELETE_SERVICE = ReconciledPaymentService
    DELETE_PERMISSION = 'HandleReversedPayments'
    OBJECT_NAME = 'Reconciled Payment'
    MODEL = ReconciledPayment
    TAG = 'Payments'



TYPES_OPTS = '|'.join(ReconciledPaymentType.to_list()).replace('(', '\(').replace(')', '\)')
RECON_TYPE_PATTERN = f"^(({TYPES_OPTS}),)*({TYPES_OPTS})?$"

class ReconciledPaymentAllResource(BaseAPIResourceAll):

    LIST_SERVICE = ReconciledPaymentService
    LIST_PERMISSION = 'ViewPayments'
    MODEL = ReconciledPayment
    TAG = 'Payments'
    FORCED_DOCS = ['post']
    ALLOWED_API_CALLER = ['post']
    SUBACTIONS = {
        'post': {
            'manual_adjustment': {
                'name': "Manual Adjustment",
                'description': "Add or remove some money from a wallet adding a note",
                'permissions': ['AdjustBalanceAndReconcilePayments'],
                'properties': ['account_id', 'amount_to_add', 'note'],
                'required': ['account_id', 'amount_to_add', 'note'],
                'presets': {
                    'source': "balance",
                    'destination': "adjustment"
                }
            }
        }
    }

    EXTRA_LIST_PARAMS = {
        'addon': {
            'in': 'query',
            'name': 'add_on_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Allows filtering reconciled payments to just one specific add-on by ID'
        },
        'addon_reference': {
            'in': 'query',
            'name': 'add_on_reference',
            'schema': {
                'type': 'string',
            },
            'example': 'C0010001-A1',
            'allowEmptyValue': True,
            'description': 'Allows filtering reconciled payments to just one specific add-on by reference'
        },
        'contract': {
            'in': 'query',
            'name': 'contract_reference',
            'schema': {
                'type': 'string',
            },
            'example': 'C0010001',
            'allowEmptyValue': True,
            'description': 'Allows filtering reconciled payments to just one specific contract'
        },
        'lead': {
            'in': 'query',
            'name': 'lead_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '123',
            'allowEmptyValue': True,
            'description': 'Allows filtering reconciled payments to just one specific lead'
        },
        'client_id': {
            'in': 'query',
            'name': 'client_id',
            'schema': {
                'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING,
            },
            'example': '123',
            'allowEmptyValue': True,
            'description': 'Allows filtering reconciled payments to just one client by ID'
        },
        'include_reversed': {
            'in': 'query',
            'name': 'include_reversed',
            'schema': {
                'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING
            },
            'example': False,
            'default': False,
            'allowEmptyValue': True,
            'description': 'Allows showing reversed reconciled payments (one result for the reconcilition and another for the reversal)'
        },
        'type': {
            'in': 'query',
            'name': 'type',
            'schema': {
                'type': 'string',
                'pattern': RECON_TYPE_PATTERN
            },
            'example': ReconciledPaymentType.addon,
            'allowEmptyValue': True,
            'description': 'Allows filtering reconciled payments of the specified types only'
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
            'description': 'Allows for filtering reconciled payments done after this time'
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
            'description': 'Allows for filtering reconciled payments done before this time'
        }
    }

    @classmethod
    def post_core(cls, data, acting_user):
        log_api.Event('Request to reconcile received. ')

        destination, amount, account, payment, contract, lead, addon, user = cls._validate_data(data, acting_user)

        if destination == 'contract':
            answer = ReconciliationService.get_answer_for_contract(contract, payment, amount, account, acting_user)
            person = contract.client.person
        elif destination == 'lead':
            answer = ReconciliationService.get_answer_for_lead(lead, payment, amount, account, user=acting_user)
            person = lead.person
        elif destination == "addon":
            answer = ReconciliationService.get_answer_for_addons(addon.contract, [addon], payment, amount, account, acting_user)
            person = addon.contract.client.person
        elif destination == "user": 
            answer = ReconciliationService.get_answer_for_user(user, payment, amount, account)
            person = user.person
        elif destination == "adjustment":
            answer = ReconciliationService.get_answer_for_adjustment(payment, amount, account, note=data.get('note'))
            person = acting_user.person
        else: #auto
            answer = PaymentRouterService.route_payment(payment, reprocessing=True)
            if not answer:
                raise Error(f'No destination found for payment {payment.Reference}')
            return {'success': True, 'message': MessageService.get_message(answer, person=acting_user.person)}, 200
        MessageService.send_answer_to_person(answer, person)
        return {'success': True, 'message': MessageService.get_message(answer, person=acting_user.person)}, 200


    @verify(permissions=['AdjustBalanceAndReconcilePayments'], schema=reconcile_payment_schema)
    @db_session(retry=2)
    def post(self):
        reconcile_data = request.json
        acting_user = get_current_api_user()
        return self.post_core(reconcile_data, acting_user)

    @staticmethod
    def _validate_data(data, acting_user):

        destination = data.get('destination')

        amount = data.get('amount', data.get('amount_to_repay'))
        invert = False
        if not amount and data.get('amount_inverted'):
            amount = data.get('amount_inverted')
            invert = True
        
        if not amount and data.get("amount_to_add"):
            amount = data.get('amount_to_add')
            invert = True
            
        if amount:
            try:
                amount = Decimal(str(amount))
                if invert:
                    amount = -amount
            except InvalidOperation:
                raise Error('The amount is incorrect')
            if amount.as_tuple()[2] < -2:
                raise Error('The amount cannot have more than 2 decimal digits')
            if amount <= 0 and data.get('destination') != 'adjustment':
                raise Error('The amount to be reconciled must be a positive number')

        account = None
        if 'account_id' in data and data['account_id']:
            account = WalletGetterService.get_from_user_and_id(acting_user, data['account_id'], strict=True)

        payment = None
        if 'payment_reference' in data and data['payment_reference']:
            try:
                reference = data['payment_reference']
                if account:
                    payment = PaymentGetterService.get_from_user_and_properties(acting_user, Reference=reference, PaymentWallet=account, strict=True)
                else:
                    wallet_operator = data.get('wallet_operator', account.operator if account else None)
                    if wallet_operator:
                        payment = PaymentGetterService.get_from_user_and_properties(acting_user, Reference=reference, wallet_operator=wallet_operator, strict=True)
                    else:
                        payment = PaymentGetterService.get_from_user_and_properties(acting_user, Reference=reference, strict=True)
            except MultipleObjectsFoundError:
                raise Error(f'Multiple payments found with the same reference {reference},  please provide a wallet operator', code="MULTIPLE_OBJECTS_FOUND")
            if not payment.remaining:
                raise Error('The payment was already used.')

        if not payment and (not amount or not account):
            raise Error('Invalid source: provide a payment_reference or account_id and amount')

        contract = ContractGetterService.get_from_user_and_properties(
            acting_user,
            reference=data.get('contract_reference')
        ) if data.get('contract_reference') else None
        if destination == 'contract' and not contract:
            raise Error('contract is required for destination "contract"')

        lead = LeadGetterService.get_from_user_and_id(acting_user, data.get('lead_id'))
        if destination == 'lead' and not lead:
            raise Error('lead_id was not provided or lead was not found')

        addon = AddonListService.get_from_user_and_properties(acting_user, reference=data.get('addon_reference')) if data.get('addon_reference') else None
        if destination == 'addon' and not addon:
            raise Error('addon was not provided or addon was not found')

        user = UserGetterService.get_from_user_and_id(acting_user, data.get('user_id'))
        if destination == 'user' and not user:
            raise Error('user_id was not provided or user was not found')

        if data.get('destination') == 'auto' and not payment:
            raise Error('You can only use "auto" with a payment_reference')

        return destination, amount, account, payment, contract, lead, addon, user

    @classmethod
    def get_meta_post(cls):
        default_name = cls._get_default_name()
        return {
                "tags": [cls.TAG],
                "permissions": cls._element_to_list(['AdjustBalanceAndReconcilePayments']),
                "summary": "ADD " + default_name + " Object",
                "requestBody": {
                    "description": "Money source data and destination data",
                    "schema": reconcile_payment_schema
                },
                "responses": {
                    200: {
                        "description": "Returns status and result message",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {
                                            "type": "boolean",
                                            "description": "Flag indicating if the reconciliation was created correctly",
                                            "example": True
                                        },
                                        "message": {
                                            "type": "string",
                                            "description": "Message describing the result of the reconciliation",
                                            "example": "Thanks for your payment! You can now introduce this token to get your system activated: 123-123-123"
                                        }
                                    }
                                }
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
