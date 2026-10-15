from constants import MAX_FLOAT_AMOUNT, MONEY_AMOUNT_PATTERN, OPTIONAL_DATETIME_OPTIONS, OPTIONAL_STRING_OPTIONS
from datetime import datetime
from decimal import Decimal
from pony.orm import PrimaryKey, Required, Optional, Set, select, composite_key
from core_system.core_entities import db
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from shared.logger.loggers import Error
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from payg_loan_system.payments.models.wallet import PaymentWalletType
from shared.services.settings_service import SettingsService


class Payment(db.Entity, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    Amount = Required(Decimal)
    Reference = Required(str)
    BackReference = Optional(str) # To be removed
    PaymentTime = Required(datetime)
    PaymentReceptionTime = Required(datetime, index=True)
    PaymentWallet = Required("PaymentWallet", column="mpesa_account")
    reversed_payment = Optional("ReversedPayment", index=True, column="reversed_payment")
    reconciled_payments = Set('ReconciledPayment', reverse="linked_payment")
    memo = Optional(str)
    wallet_operator = Optional(str, index=True)
    country = Optional(str)
    currency = Optional(str)
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    back_payment = Optional('Payment', reverse="back_payment", column="back_payment")
    payment_uuid = Optional(str, index=True)
    status = Optional(str)

    # Cached properties
    cached_remaining_positive = Optional(bool, default=False, index=True, volatile=True)
    processed = Required(bool, default=False, index=True, volatile=True)

    check_coherence_flag = True

    composite_key(Reference, wallet_operator)

    def __repr__(self):
        return f'Payment[{self.id}:{self.Reference}]'

    @property
    def transaction_id(self):
        return self.Reference

    @property
    def reversed(self):
        return self.reversed_payment and self.reversed_payment.reconciled_payment

    @property
    def used(self):
        return self.reconciled_payments or self.PaymentWallet.get_balance() < self.Amount

    @property
    def remaining(self):
        '''Calculates the remaining amount available for use in a payment. 
        
        It takes into consideration that payments can be negative and that
        if the balance of the wallet is less than the remaining amount, only
        the balance can be used, not all the remaining amount. It also accounts
        for the possibility of errors where the balance has the opposite sign
        of the payment. In that case, to avoid using more than what is available 
        in the payment, the amount is capped at 0
        '''
        return (
            (self.Amount >= 0) * min(
                self.Amount - self.total_reconciled,
                max(0, self.PaymentWallet.balance)
            ) +
            (self.Amount < 0) * max(
                self.Amount - self.total_reconciled,
                -max(0, -self.PaymentWallet.balance)
            )
        )

    @property
    def total_reconciled(self):
        return select(r.amount for r in self.not_reversed_reconciliations).sum()

    @property
    def not_reversed_reconciliations(self):
        return self.reconciled_payments.filter(lambda r: not r.converse)

    @property
    def orphaned(self):
        return bool(self.remaining) and not self.reversed

    @property
    def orphaned_cached(self):
        return self.cached_remaining_positive and not self.reversed
    
    @property
    def label(self):
        return self.Reference + (' (partially used)' if self.remaining < self.Amount else '')

    @property
    def reversable_use(self):
        reconciled = self.reconciled_payments
        unreversable_addon = reconciled.filter(lambda r: r.add_on is not None and r.converse is None)
        unreversable_down = reconciled.filter(lambda r: r.repayment and r.repayment.discount_type == ContractRepaymentDiscountTypes.downpayment)
        return reconciled and not (unreversable_addon or unreversable_down)

    @property
    def reversable(self):
        return self.PaymentWallet.Type != PaymentWalletType.agent_collection and (not self.used or self.reversable_use)

    def get_operator_label(self):
        return 'Mobile Money: {}' if self.wallet_operator else ('Mobile Money Wallet' if self.PaymentWallet.Type == PaymentWalletType.mobile_money else 'Cash Wallet')
    
    def get_related_entities(self):
        return [r.get_related_entity() for r in self.reconciled_payments]

    def GetSpecialPayerName(self):
        frontPayment = self.back_payment
        if frontPayment is not None:
            Client = frontPayment.PaymentWallet.client
            if Client is not None:
                return 'client ' + str(Client.id) + ' (' + Client.full_name + ')'
            else:
                return 'unknown client (' + frontPayment.PaymentWallet.FullName + ')'
        return None

    @property
    def client(self):
        return self.PaymentWallet.client or (self.back_payment.PaymentWallet.client if self.back_payment else None)

    def check_data_coherence(self):
        if self.check_coherence_flag:
            if self.Amount <= 0 and not SettingsService.get_setting('FeatureToggles').get('OffTaking', False):
                raise Exception('INVALID_AMOUNT_TOO_LOW for negative payment with no off-taking feature enabled')
            if self.Amount > MAX_FLOAT_AMOUNT:
                raise Exception('INVALID_AMOUNT_TOO_LARGE')
            if round(self.Amount, 2) != self.Amount:
                raise Exception('INVALID_AMOUNT_TOO_MANY_DIGITS')
            if self.remaining < 0 and not SettingsService.get_setting('FeatureToggles').get('OffTaking', False):
                raise Exception('TOTAL_RECONCILED_MORE_THAN_AVAILABLE ['+self.Reference+']')

    def before_insert(self):
        self.check_data_coherence()
        self.payment_or_reconciled_changed()

    def after_insert(self):
        self.process_hooks()

    def before_update(self):
        self.check_data_coherence()
        self.modifiedDate = datetime.now()
        self.payment_or_reconciled_changed()

    def after_update(self):
        self.process_hooks()

    def process_hooks(self):
        self.PaymentWallet.payment_or_reconciled_changed()

    def payment_or_reconciled_changed(self):
        self.cached_remaining_positive = (self.remaining > 0) if self.Amount > 0 else (self.remaining < 0)

    @classmethod
    def get_model_definition(cls, op, include_destination=True, alternate_model=None, **kwargs):
        definition = {
            "properties": {
                "reference": {
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "description": "See `transaction_id`",
                    "deprecated": True
                },
                'transaction_id': {
                    "description": "This is the identifier of the payment (must be unique for a given `wallet_operator`), it is automatically generated by the Mobile Money provider.",
                    "type": "string",
                    "example": "A1234B5678",
                    "value": lambda o: o.Reference
                },
                "amount": {
                    "description": "This is the Amount of the payment, in the local currency of the PAYG platform instance",
                    "example": 12345.53,
                    "value": lambda o: o.Amount,
                    "oneOf": [{
                        "type": "string",
                        "pattern": MONEY_AMOUNT_PATTERN
                    }, {
                        "type": "number",
                        "format": "float"
                    }]
                },
                "sender_name": {
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "description": "See `wallet_name`",
                    "deprecated": True
                },
                'wallet_name': {
                    "description": "This is the name of the account made FROM DATA PROVIDED BY THE TELCO, it must be A UNIQUE IDENTIFIER for a given `wallet_operator`. In many case it can be the same as the MSISDN or Client Name + MSISDN together to ensure uniqueness.",
                    "type": "string",
                    "example": "JOHN DOE (25512341234)",
                    "value": lambda o: o.PaymentWallet.FullName
                },
                "sender_msisdn": {
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "description": "See `wallet_msisdn`",
                    "deprecated": True,
                },
                "sender_phone_number": {
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "description": "See `wallet_msisdn`",
                    "deprecated": True,
                },
                'wallet_msisdn': {
                    "description": "This is the MSISDN (phone number in MSISDN format) of the owner of the account, if provided. Note that this should be unique.",
                    "type": "string",
                    "format": "phone",
                    "example": "+25512341234",
                    "value": lambda o: o.PaymentWallet.phone_number.number if o.PaymentWallet.phone_number else ''
                },
                'sent_datetime': {
                    "description": "This is the date and time at which the payment was originally sent, in ISO 8601 format",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.PaymentTime
                },
                'reception_datetime': {
                    "description": "This is the date and time at which the payment was received on PaygOps, in ISO 8601 format",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.PaymentReceptionTime
                },
                'memo': {
                    "description": "This is a note manually entered by the client, it can be used to better match the payment to a client (e.g. using their Device serial number or contract reference, etc.).",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "C12345",
                    "value": lambda o: o.memo
                },
                'note': {
                    "description": "See `memo`.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "deprecated": True,
                },
                'wallet_operator': {
                    "description": "This property is optional but strongly recommended, and not providing it may result in unexpected behaviour or errors when there are multiple payment integrations as `transaction_id` and `wallet_name` are not necessarily unique accross different operators.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "MPESA",
                    "value": lambda o: o.wallet_operator
                },
                'country': {
                    "description": "Code of country from which the payment was sent",
                    "example": "TZ",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "value": lambda o: o.country
                },
                'currency': {
                    "description": "Code of the currency in which the payment was sent",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "TZS",
                    "value": lambda o: o.currency
                },
                "uuid": {
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "description": "Unique ID that is not needed anymore",
                    "deprecated": True
                }
            },
            "allOf": [
                {
                    "oneOf": [
                        {"required": ["reference"]},
                        {"required": ["transaction_id"]}
                    ],
                },
                {
                    "oneOf": [
                        {"required": ["sender_name"]},
                        {"required": ["wallet_name"]}
                    ],
                },
            ],
            "create_required": ['amount', 'transaction_id', 'wallet_name'],
            "create_allowed": [],
            "create_forbidden": ['reception_datetime', "destinations", "destination", "destination_type"],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_forbidden": ['reference', "sender_name", "sender_msisdn", "sender_phone_number", "uuid", "note"],
            "view_allowed": None,
            "validate_required": ['amount', 'transaction_id', 'wallet_name'],
            "validate_forbidden": ['reference', "sender_name", "sender_msisdn", "sender_phone_number", "destinations", 'reception_datetime', "destination", "destination_type", "uuid", "note"],
            "validate_allowed": None,
        }
        if include_destination:
            DESTINATION_SCHEMA = {
                "destination_type": {
                    "type": "string",
                    "description": "The code of the destination of the payment (if clear destination). Note that `contract_repayment` can mean either an actual contract payment or a pending contract payment (or a mix of both). ",
                    "enum": ["contract_repayment", "lead", "add_on", "user", "client"],
                    "example": "contract_repayment",
                },
                "destination": {
                    "description": "If the destination is `contract_repayment`, `lead` or `add_on` then this field contains the reference of the contract involved. If it is `user`, the user ID, otherwise not present",
                    "type": "string",
                    "example": "C00001",
                },
                "repayment_id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The id of the repayment to which the money was reconciled (if any)",
                },
                "lead_id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the lead to which the money was reconciled to (if any)",
                },
                "user_id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the user to which the money was reconciled to (if any)",
                },
                "client_id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the client to which the money was reconciled to (if any)",
                },
                "add_on_reference": {
                    "type": "string",
                    "example": "C1202003-A3",
                    "description": "The reference of the add-on to which the money was reconciled to (if any)",
                },
                "contract_reference": {
                    "type": "string",
                    "example": "C1202003",
                    "description": "The reference of the contract to which the money was reconciled (if any)",
                },
                "reversed": {
                    "type": "boolean",
                    "example": False,
                    "description": "Whether the payment was reversed or not",
                },
                
            }
            definition['properties'].update({
                'destinations': {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": DESTINATION_SCHEMA
                    },
                    "value": lambda o: o.get_destination_indicator(include_destination_details=True)
                },
            })
            definition['properties'].update({
                "destination_type": {
                    "type": "string",
                    "description": "The code of the destination of the payment (if clear destination). Note that `contract_repayment` can mean either an actual contract payment or a pending contract payment (or a mix of both). ",
                    "enum": ["contract_repayment", "lead", "add_on", "user", "client"],
                    "example": "contract_repayment",
                    "deprecated": True,
                    "value": lambda o: o.get_first_indicator().get('destination_type')
                },
                "destination": {
                    "description": "If the destination is `contract_repayment`, `lead` or `add_on` then this field contains the reference of the contract involved. If it is `user`, the user ID, otherwise not present",
                    "type": "string",
                    "example": "C00001",
                    "deprecated": True,
                    "value": lambda o: o.get_first_indicator().get('destination')
                },
            })
        if alternate_model == 'b2c_payment':
            definition['properties'].update({
                'transaction_id': {
                    "description": "This is the identifier of the payment (must be unique for a given `wallet_operator`), it is automatically generated by the Mobile Money provider.",
                    "type": "string",
                    "example": "A1234B5678",
                    "value": lambda o: o.Reference if o.Reference != o.payment_uuid else None
                },
                "payment_uuid": {
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "description": "Unique ID for b2c payments",
                    "example": "123e4567-e89b-12d3-a456-426614174000",
                    "value": lambda o: o.payment_uuid
                },
                "status": {
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "description": "Status of the payment",
                    "example": "Pending",
                    "value": lambda o: o.status
                }
            })
            del definition['properties']['destinations']
            del definition['properties']['destination_type']
            del definition['properties']['destination']
            del definition['properties']['reception_datetime']
            definition['create_required'] = ['amount', 'wallet_msisdn', 'payment_uuid']
            definition['edit_allowed'] = ['transaction_id', 'status', 'reception_datetime', 'currency', 'country']
            del definition['allOf']
        return definition
    
    def get_first_indicator(self):
        if self.reconciled_payments:
            for r in self.reconciled_payments:
                # Only return the first
                return r.get_destination_indicator()
        return {}

    def get_destination_indicator(self, include_destination_details=False):
        if self.reconciled_payments:
            return [r.get_destination_indicator(include_destination_details=include_destination_details) for r in self.reconciled_payments]
        return []
