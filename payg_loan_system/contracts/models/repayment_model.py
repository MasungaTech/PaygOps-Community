from datetime import datetime
from decimal import Decimal
from pony.orm import PrimaryKey, Required, Optional, Set, select
from core_system.core_entities import db
from payg_loan_system.offers.models import OfferType
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from shared.logger.loggers import Error
from shared.api_helpers.model_definition_base import ModelDefinitionMixin


class ContractRepayment(db.Entity, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    contract = Required('Contract', column="contract")
    time = Required(datetime)
    expected_time = Optional(datetime)
    next_repayment_due_time = Optional(datetime)
    delay_given_in_hours = Optional(Decimal, scale=4, default=0) # Support fraction of hours, second resolution
    credit_value = Optional(Decimal)
    credit_unit = Optional(str)
    amount = Required(Decimal, default=0)
    amount_paid = Required(Decimal, default=0)
    amount_discounted = Required(Decimal, default=0)
    discount_type = Optional(str, py_check=ContractRepaymentDiscountTypes.ovalid)
    contract_event = Optional('ContractEvent')
    reconciled_payments = Set('ReconciledPayment')
    token = Optional("Token")
    processed = Required(bool, default=False, index=True)
    converse = Optional("ContractRepayment", reverse="converse", column="converse")
    addons = Set("ContractAddOn", reverse="repayments")

    # Computed
    hours_late = Optional(Decimal, scale=4) # Support fraction of hours, second resolution
    amount_late = Optional(Decimal)

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    @property
    def total_reconciled(self):
        return select(r.amount for r in self.reconciled_payments.select()).sum()

    @property
    def orphaned_simple_payment(self):
        return not self.converse and self.amount > 0 and not self.discount_type and not self.reconciled_payments

    def get_total_paid_at_time(self):
        return self.contract.get_cumulative_amount_repaid(self.time)

    def get_expected_total_paid_at_time(self, cached=False):
        return self.contract.get_expected_amount_repaid(self.time, cached=cached)

    def get_percentage_paid_at_time(self):
        total_value = self.contract.get_total_value()
        if self.contract.offer.type == OfferType.time_based or self.contract.offer.type == OfferType.usage_based:
            return None
        if total_value == 0:
            return Decimal(1)
        return self.get_total_paid_at_time() / self.contract.get_total_value()

    def get_source_reconciled_payments(self):
        payment = self.converse if self.discount_type in [ContractRepaymentDiscountTypes.reversal, ContractRepaymentDiscountTypes.downpayment_reversal] else self
        return payment.reconciled_payments

    def get_credit_bought(self):
        return self.amount/self.contract.get_base_price_per_credit()

    def check_data_coherence(self):
        if round(self.amount, 2) != self.amount:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')

        if round(self.amount_paid, 2) != self.amount_paid:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')

        if round(self.amount_discounted, 2) != self.amount_discounted:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')

        if self.amount_late and self.amount_late.as_tuple()[2] < -2:
            self.amount_late = round(self.amount_late, 2)

        if self.amount != self.amount_paid + self.amount_discounted:
            raise Error('INCOHERENT_REPAYMENT_AMOUNTS')

        if self.hours_late and self.hours_late.as_tuple()[2] < -4:
            raise Error('HOURS_LATE_TOO_MANY_DIGITS')

    def before_insert(self):
        self.check_data_coherence()

    def before_update(self):
        self.check_data_coherence()
        self.modifiedDate = datetime.now()

    def after_insert(self):
        self.contract.update_cached_data(repayment_created=True)
        for addon in self.addons:
            addon.update_cached_properties()

    def after_update(self):
        self.contract.update_cached_data(repayment_created=True)
        for addon in self.addons:
            addon.update_cached_properties()

    def before_delete(self):
        raise Exception('Attempt to delete a repayment')

    @property
    def downpayment(self):
        return self.discount_type == ContractRepaymentDiscountTypes.downpayment

    @property
    def reversable(self):
        return not self.converse and self.discount_type not in [
            ContractRepaymentDiscountTypes.manual_adjustment,
            ContractRepaymentDiscountTypes.manual_delay,
            ContractRepaymentDiscountTypes.manual_discount,
            ContractRepaymentDiscountTypes.offer_change,
            ContractRepaymentDiscountTypes.offer_change_delay,
            ContractRepaymentDiscountTypes.rounding,
            ContractRepaymentDiscountTypes.special_delay,
            ContractRepaymentDiscountTypes.purchasing_addon
        ]

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "description": "The ID of the repayment item",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.id
                },
                'date': {
                    "description": "This is the date of the repayment ",
                    "oneOf": [
                        {
                            "type": "string",
                            "format": "date-time",
                        },
                        {
                            "type": "null",
                        }
                    ],
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.time
                },
                'expected_date': {
                    "description": "This is the expected date of the contact payment ",
                    "oneOf": [
                        {
                            "type": "string",
                            "format": "date-time",
                        },
                        {
                            "type": "null",
                        }
                    ],
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.expected_time
                },
                'next_due_date': {
                    "description": "This is the expected date of the next contract payment ",
                    "oneOf": [
                        {
                            "type": "string",
                            "format": "date-time",
                        },
                        {
                            "type": "null",
                        }
                    ],
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.next_repayment_due_time
                },
                'type': {
                    "description": "The type of the repayment",
                    "type": "string",
                    "enum": ContractRepaymentDiscountTypes.to_list()+['Contract Payment'],
                    "example": 'Downpayment',
                    "value": lambda o: o.discount_type or "Contract Payment"
                },
                'contract_reference': {
                    "description": "The reference of the contract the repayment is on",
                    "type": "integer",
                    "example": 4,
                    "value": lambda o: o.contract.reference
                },
                'client_id': {
                    "description": "The ID of the client owning the contract the repayment is on",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.contract.client.id
                },
                'total_amount': {
                    "description": "The total amount of that repayment",
                    "type": "number",
                    "example": 12,
                    "value": lambda o: o.amount
                },
                'amount_paid': {
                    "description": "The amount paid for that repayment",
                    "type": "number",
                    "example": 12,
                    "value": lambda o: o.amount_paid
                },
                'amount_discounted': {
                    "description": "The amount given as discount for that repayment",
                    "type": "number",
                    "example": 12,
                    "value": lambda o: o.amount_discounted
                },
                'reconciled_payments': {
                    "description": "The ID of the reconciled payments used to make the contract payment (if any)",
                    "type": "array",
                    "example": [23, 45, 37],
                    "value": lambda o: [r.id for r in o.reconciled_payments]
                },
                "reversed": {
                    "type": "boolean",
                    "example": False,
                    "description": "Wheather the repayment was reversed or not",
                    "value": lambda o: bool(o.converse)
                },
                "reversed_by": {
                    "type": "integer",
                    "example": 123,
                    "description": "The id of the repayment that reverses the current repayment (if any)",
                    "value": lambda o: o.converse.id if o.converse else None
                },
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }