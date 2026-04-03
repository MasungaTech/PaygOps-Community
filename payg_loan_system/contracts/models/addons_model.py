from datetime import datetime
from decimal import Decimal

from flask import url_for
from pony import orm
from pony.orm import Optional, Required, Set, coalesce, sum

from constants import (BOOLEAN_OPTIONAL_OPTIONS, FLOAT_OPTIONAL_OPTIONS,
                       INTEGER_OPTIONAL_OPTIONS, INTEGER_PATTERN,
                       MONEY_AMOUNT_PATTERN, OPTIONAL_STRING_OPTIONS,
                       REQUIRED_STRING_PATTERN)
from core_system.core_entities import db
from core_system.operational_entities.models import OperationalEntity
from payg_loan_system.contracts.models.addon_bundle_model import \
    ContractAddOnBundleItem
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.contracts.models.addon_loan_extension_mode import \
    AddOnLoanExtensionMode
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.reconciled_payment_type import \
    ReconciledPaymentType
from payg_loan_system.contracts.models.repayment_discount_types import \
    ContractRepaymentDiscountTypes
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from payg_loan_system.offers.models import OfferType
from shared.api_helpers.client_helpers.uuid_generation_helpers import \
    generate_uuid
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.helpers.db_helpers import TypeClassBase
from shared.helpers.many_to_many_helpers import add_many_to_many_schema
from shared.helpers.version_changes import get_object_changes
from shared.logger.loggers import Error


class ContractAddOn(db.Entity, ModelDefinitionMixin):

    contract = Optional('Contract', column="contract")
    lead = Optional("Lead", column="lead")

    reference = Required(str, unique=True)
    # Used for payment purposes, can do contract number -A1, A2, A3
    offer_version = Required('AddOnOfferVersion', column="offer")
    device = Optional('Device', column="device" , reverse="addon")

    quantity_sold = Required(Decimal, default=1)
    total_amount = Required(Decimal)
    discounted_amount = Required(Decimal, default=0)

    loan_mode = Optional(str, py_check=AddOnLoanExtensionMode.ovalid)
    repayment_increase = Required(Decimal, default=0)

    time_created = Required(datetime, index=True)
    time_approved = Optional(datetime, index=True)
    time_paid = Optional(datetime, index=True)
    time_canceled = Optional(datetime)
    planned_delivery_date = Optional(datetime, index=True)

    sale_approved_by = Optional('User', reverse='add_ons_approved', column="sale_approved_by")
    sale_made_by = Optional('User', reverse='add_ons_sold', column="sale_made_by")
    canceled_by = Optional('User', reverse="add_ons_canceled", column="canceled_by")

    reconciled_payments = Set('ReconciledPayment')
    note = Optional(str)
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = Optional(str, unique=True)

    billed_items = Set('BilledItem')
    contract_event = Optional('ContractEvent')

    cancelled_addon = Optional("ContractAddOn", column="cancelled_addon")
    cancelled_by_addon = Optional("ContractAddOn", reverse="cancelled_addon")

    delivered = Required(bool, default=False, index=True)
    delivery_date = Optional(datetime, index=True)

    device_event = Set("ContractEvent", reverse="device_addon")
    quantity_stock_locations = Set('QuantityStockLocation')

    repayments = Set('ContractRepayment')

    # Cached properties
    cached_paid = Optional(bool, default=False, index=True, volatile=True)
    cached_person = Required('Person', index=True, column="cached_person", volatile=True)

    STATUSES = ["cancelled", "paid", "pending", "onloan", "unpaid", "free"]

    def __repr__(self):
        return f'ContractAddOn[{self.id}:{self.reference}]'

    @property
    def status(self):
        for st in self.STATUSES:
            if getattr(self, st):
                return st

    @property
    def downpayment(self):
        return coalesce(self.offer_version.downpayment, 0)*self.quantity_sold

    @property
    def principal(self):
        return self.total_amount-self.downpayment

    @property
    def already_paid(self):
        return sum(r.amount for r in self.reconciled_payments if not r.converse)

    @property
    def already_paid_purchasing(self):
        return self.already_paid - sum(r.amount for r in self.repayments if not r.converse)

    def get_reconciled_payments_for_downpayment(self, downpayment):
        previous_downpayment = downpayment.contract.repayments.select(
            lambda r: r.discount_type == ContractRepaymentDiscountTypes.downpayment and r.time < downpayment.time
        ).order_by(lambda r: orm.desc(r.time)).first()
        recons = self.reconciled_payments.select(lambda r: r.time <= downpayment.time)
        if previous_downpayment:
            recons = recons.filter(
                lambda r: r.time > previous_downpayment.time and r.type != ReconciledPaymentType.addon_payment_reversal
            )
        return recons

    @property
    def to_pay(self):
        return (self.downpayment or self.total_amount)-self.already_paid-self.discounted_amount

    @property
    def paid_for_leads(self): # needed cause checking if cancelled would filter out addons on leads
        return (
            self.free or self.already_paid == (self.total_amount-self.discounted_amount)
        ) and self.offer_version.offer.type == AddOnType.lump_sum

    @property
    def paid(self):
        return self.offer_version.offer.type == AddOnType.lump_sum and not self.cancelled and (
            (self.free and bool(self.sale_approved_by)) or (
                not self.free and self.already_paid == (self.total_amount-self.discounted_amount)
            ) or (
                not self.free and self.offer_version.offer.purchasing_addon and self.already_paid_purchasing == (self.total_amount-self.discounted_amount)
            )
        ) and (
            not self.offer_version.offer.purchasing_addon or (
                bool(self.contract) and
                self.contract.offer.type == OfferType.lump_sum and
                self.already_paid_purchasing == self.total_amount
            )
        )

    @property
    def downpayment_paid(self):
        return self.offer_version.offer.type != AddOnType.lump_sum and self.to_pay == 0

    @property
    def extension_days(self):
        if self.offer_version.offer.type == AddOnType.loan_duration_change:
            return self.offer_version.duration_change*self.quantity_sold
        if self.offer_version.offer.type not in [
            AddOnType.loan, AddOnType.deposit_change
        ] or self.loan_mode != AddOnLoanExtensionMode.duration:
            return 0
        # For leads: We use for all the leads addon the offer price for leads to ensure the
        # resulting loan is independent of the order of addition of addons that is equivalent
        # to first adding duration addons and then repayment amount addons (i.e. duration
        # addons cannot see repayment addons but repayments addons can see duration addons)
        if self.lead:
            price = self.lead.offer.base_price_amount
        else:
            price = self.contract.reference_price_at(self.time_approved or datetime.now())

        regular_value = self.principal if not self.contract else self.total_amount-self.already_paid
        is_deposit_change = self.offer_version.offer.type == AddOnType.deposit_change
        value = -self.downpayment if is_deposit_change else regular_value
        return value/price*getattr(self.contract or self.lead, 'offer').base_price_credit

    @property
    def free(self):
        return (
            self.total_amount == self.discounted_amount
            and not self.offer_version.offer.purchasing_addon
        )

    @property
    def excluded_effects(self):
        return (
            self.time_canceled and
            not self.cancelled_by_addon and
            bool(self.contract) and self.contract.status != 'Cancelled'
        )

    def excluded_effects_at(self, time):
        return (
            self.time_canceled is not None and
            self.time_canceled <= time and not self.cancelled_by_addon and
            bool(self.contract) and self.contract.status != 'Cancelled'
        )

    @property
    def cancelled(self):
        return (
            self.time_canceled is not None or
            self.cancelled_addon is not None or
            (self.contract and self.contract.status == 'Cancelled')
        )

    @property
    def cancelled_not_contract(self):
        return (
            self.time_canceled is not None or
            self.cancelled_addon is not None
        )

    @property
    def purchasing(self):
        return   self.offer_version.offer.purchasing_addon

    @property
    def cancelled_by_contract(self):
        return (not self.time_canceled) and (self.contract and self.contract.status == 'Cancelled')

    @property
    def pending(self):
        return (not self.sale_approved_by and not self.cancelled)

    @property
    def not_lead(self):
        return self.contract is not None

    @property
    def onloan(self):
        return self.offer_version.offer.type != AddOnType.lump_sum and self.sale_approved_by

    @property
    def onloan_not_cancelled(self):
        return self.onloan and not self.cancelled and not self.contract.status == 'Defaulted'

    @property
    def manually_cancelled(self):
        return (self.time_canceled) and (self.contract) or self.cancelled_addon

    @property
    def loan(self):
        return self.onloan

    @property
    def unpaid(self):
        return not self.paid and self._extra_conditions_unpaid

    @property
    def cached_unpaid(self):
        return not self.cached_paid and self._extra_conditions_unpaid

    @property
    def _extra_conditions_unpaid(self):
        return (self.offer_version.offer.type == AddOnType.lump_sum
            and not self.cancelled
            and not self.pending
            and not self.free
            and not self.defaulted
            and (
                not self.offer_version.offer.purchasing_addon
                or (
                    bool(self.contract) and
                    self.contract.offer.type == OfferType.lump_sum
                )
            )
        )

    @property
    def defaulted(self):
        return bool(self.contract) and self.contract.status == ContractStatus.defaulted

    @property
    def defaulted_not_manually_cancelled(self):
        return self.defaulted and not self.cancelled_by_addon and not self.cancelled_addon and not self.pending

    def derived_planned_delivery_date(self):
        if self.planned_delivery_date:
            return self.planned_delivery_date
        elif self.lead:
            return self.lead.agreedDeliveryDate

    @property
    def not_delivered(self):
        return not self.delivered and not self.pending and not self.cancelled

    def delivery_date_with_default(self):
        return self.delivery_date if self.delivery_date else self.contract.start_time if (self.contract and self.delivered) else None

    def can_be_delivered(self):
        return self.offer_version.offer.can_be_delivered()

    def check_data_coherence(self):
        if round(self.total_amount, 2) < self.total_amount or round(self.discounted_amount, 2) != self.discounted_amount:
            raise Exception('INVALID_AMOUNT_TOO_MANY_DIGITS')

        if self.total_amount != round(self.quantity_sold*self.offer_version.price, 2):
            raise Exception('TOTAL_AMOUNT_NOT_COHERENT')

        if self.offer_version.offer.type == AddOnType.loan and self.discounted_amount:
            raise Exception('LOAN_ADDONS_CANNOT_BE_DISCOUNTED')

        if self.loan_mode == AddOnLoanExtensionMode.amount and self.repayment_increase == 0 and self.contract and self.sale_approved_by and self.total_amount != 0:
            raise Exception('REPAYMENT_INCREASE_NOT_COHERENT')

    def get_link(self):
        return url_for('contract.view_addon', addon_reference=self.reference)

    def get_display_id(self):
        return str(self.reference)
    
    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
        self.check_data_coherence()
        self.update_cached_properties()
        
    def before_update(self):
        self.check_data_coherence()
        self.update_cached_properties()
        self.modifiedDate = datetime.now()

    def update_cached_properties(self):
        self.cached_paid = self.paid
        if not self.cached_person:
            self.cached_person = self.get_person()

    def get_person(self):
        return self.contract.client.person if self.contract else self.lead.person

    def after_insert(self):
        if self.contract:
            self.contract.update_cached_data(contract_terms_changed=True)
        if self.lead:
            self.lead.before_update()

    def after_update(self):
        if self.contract:
            self.contract.update_cached_data(contract_terms_changed=True)
        if self.lead:
            self.lead.before_update()

    def calculate_current_repayment_increase(self, excluded_addon_ids=[]):
        if self.offer_version.offer.type == AddOnType.lump_sum or (self.offer_version.offer.type == AddOnType.loan and self.loan_mode != AddOnLoanExtensionMode.amount) or (self.offer_version.offer.type == AddOnType.deposit_change and self.loan_mode != AddOnLoanExtensionMode.amount):
            return 0
        if not self.lead:
            # Here we need to calculate right before this addon was added
            time = self.time_approved if self.time_approved else datetime.now()
            installments = self.contract.get_number_installments(time=time, add_on_id=self.id, excluded_addon_ids=excluded_addon_ids)
            if installments in [0,1] and self.contract.offer.base_price_amount_can_be_negative:
                installments = self.contract.offer.get_time_to_pay()/self.contract.offer.base_price_credit
            if self.offer_version.offer.type == AddOnType.loan_duration_change:
                value = -self.extension_days*self.contract.get_base_price_per_credit(time=time, add_on_id=self.id)
                installments += self.extension_days/self.contract.offer.base_price_credit
            else:
                value = self.total_amount-self.already_paid
        else:
            if self.lead.offer.base_price_credit == 0:
                raise Error('The reference pricing duration of the offer cannot be 0 days')
            installments = (self.lead.offer.get_time_to_pay()+self.lead.total_extended)/self.lead.offer.base_price_credit
            if self.offer_version.offer.type == AddOnType.loan_duration_change:
                value = -self.extension_days*self.lead.offer.get_base_price_per_credit() if self.lead.offer.get_base_price_per_credit() != 0 else 0
            elif self.offer_version.offer.type == AddOnType.deposit_change:
                value = -self.downpayment
            else:
                value = self.principal
        if not installments:
            return 0
        return round(value/installments, 2)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "description": "The Id of the Add-on",
                    "example": 123,
                    "value": lambda o: o.id
                },
                'reference': {
                    "type": "string",
                    "description": "The reference of the Add-on",
                    "example": "C1234001-A0",
                    "value": lambda o: o.reference
                },
                'contract_reference': {
                    "type": "string",
                    "description": "The reference of contract of the Add-on. Use either this or lead_id when creating. ",
                    "example": "C1234001",
                    "value": lambda o: getattr(o.contract, 'reference', None)
                },
                'lead_id': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }, {
                        "type": "null"
                    }, { 
                        "type": "string", 
                        "maxLength": 0
                    }],
                    "description": "The Id of the lead to which the Add-on was attached, only has a value if the add-on was sold in pre-sales stage. Use either this or contract_reference when creating.",
                    "example": 123,
                    "value": lambda o: getattr(o.lead, 'id', None)
                },
                'lead': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }, {
                        "type": "null"
                    }, { 
                        "type": "string", 
                        "maxLength": 0
                    }],
                    "description": "The Id of the lead to which the Add-on was attached, only has a value if the add-on was sold in pre-sales stage",
                    "example": 123,
                    "value": lambda o: getattr(o.lead, 'id', None),
                    "deprecated": True
                },
                'offer_code': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": REQUIRED_STRING_PATTERN
                    }, {
                        "type": "null"
                    }],
                    "description": "The code of the Add-on offer, when setting this property, pricing data used for this add-on will be taken for the version available for sales",
                    "example": "OFFER_1",
                    "value": lambda o: o.offer_version.offer.code
                },
                'offer_name': {
                    "type": "string",
                    "pattern": REQUIRED_STRING_PATTERN,
                    "description": "The name of the Add-on offer",
                    "example": "Offer 1",
                    "value": lambda o: o.offer_version.offer.name
                },
                'offer_version_id': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }, {
                        "type": "null"
                    }],
                    "description": "The Id of the Add-on offer version",
                    "example": 12,
                    "value": lambda o: o.offer_version.id
                },
                'offer_id': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }, {
                        "type": "null"
                    }],
                    "description": "The Id of the Add-on offer",
                    "example": 12,
                    "value": lambda o: o.offer_version.offer.id
                },
                'offer': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }, {
                        "type": "null"
                    }, { 
                        "type": "string", 
                        "maxLength": 0
                    }],
                    "description": "The Id of the Add-on offer version",
                    "example": 12,
                    "value": lambda o: o.offer_version.id,
                    "deprecated": True
                },
                'loan_mode': {
                    "type": "string",
                    "description": "The type of loan extension",
                    "enum": AddOnLoanExtensionMode.to_list(),
                    "value": lambda o: o.loan_mode if o.offer_version.offer.type != AddOnType.lump_sum else None,
                },
                'type': {
                    "type": "string",
                    "description": "The type of add-on",
                    "enum": AddOnType.to_list(),
                    "value": lambda o: o.offer_version.offer.type,
                },
                'quantity_sold': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": MONEY_AMOUNT_PATTERN
                    }, {
                        "type": "number",
                        "format": "float"
                    }],
                    "description": "Amount sold of the Add-on",
                    "example": 12.20,
                    "value": lambda o: float(o.quantity_sold)
                },
                'device_serial': {
                    "description": "The Serial Number of the device sold with the add-on",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "NPG-12345",
                    "value": lambda o: o.device.composed_serial if o.device else None
                },
                'total_amount': {
                    "type": "number",
                    "description": "Total Value of the sale of the Add-on",
                    "example": 12.20,
                    "value": lambda o: float(o.total_amount)
                },
                'discounted_amount': {
                    "type": "number",
                    "description": "Amount discounted from the total value of the price",
                    "example": 12.20,
                    "value": lambda o: float(o.discounted_amount)
                },
                'time_created': {
                    "type": "string",
                    "format": "date-time",
                    "description": "Date and time at which the add-on was created",
                    "example": "2020-04-03T23:30:34",
                    "value": lambda o: o.time_created.isoformat()
                },
                'paid': {
                    "type": "boolean",
                    "description": "Boolean flag indicating if the add-on has been paid",
                    "example": True,
                    "value": lambda o: o.paid
                },
                'time_paid': {
                    "type": "string",
                    "format": "date-time",
                    "description": "Date and time at which the add-on was paid, if applicable",
                    "example": "2020-04-03T23:30:34",
                    "value": lambda o: o.time_paid.isoformat() if o.time_paid else None
                },
                'cancelled': {
                    "type": "boolean",
                    "description": "Boolean flag indicating if the add-on has been cancelled",
                    "example": True,
                    "value": lambda o: o.cancelled
                },
                'time_cancelled': {
                    "type": "string",
                    "format": "date-time",
                    "description": "Date and time at which the add-on was cancelled, if applicable",
                    "example": "2020-04-03T23:30:34",
                    "value": lambda o: o.time_canceled.isoformat() if o.time_canceled else None
                },
                'cancelled_by': {
                    "type": "integer",
                    "description": "Id of the user that cancelled the add-on, if applicable",
                    "example": 123,
                    "value": lambda o: getattr(o.canceled_by, 'id', None)
                },
                'reconciled_payments': {
                    "type": "array",
                    "items": {
                        "type": "integer",
                    },
                    "example": [12, 13, 14],
                    "description": "List of Ids of reconciled payments used to paid the add-on",
                    "value": lambda o: [r.id for r in o.reconciled_payments]
                },
                'approved': {
                    "type": "boolean",
                    "description": "Boolean flag indicating if the add-on has been approved. ",
                    "example": True,
                    "value": lambda o: not o.pending
                },
                'approved_by': {
                    "type": "integer",
                    "description": "Id of the user that approved the add-on, if applicable. If `approved` is set this will be set to the user making the request. ",
                    "example": 123,
                    "value": lambda o: getattr(o.sale_approved_by, 'id', None)
                },
                'sold_by': {
                    "type": "integer",
                    "description": "Id of the user that created (sold) the add-on, if applicable",
                    "example": 123,
                    "value": lambda o: getattr(o.sale_made_by, 'id', None)
                },
                'status': {
                    "type": "string",
                    "enum":  ['paid', 'pending', 'onloan', 'unpaid'],
                    "description": "The status of the add-on",
                    "value": lambda o: o.status
                },
                'already_paid': {
                    "type": "number",
                    "description": "Amount already paid of the total value of the add-on",
                    "example": 10.34,
                    "value": lambda o: float(o.already_paid)
                },
                "client_id": {
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }, {
                        "type": "null"
                    }, { 
                        "type": "string", 
                        "maxLength": 0
                    }],
                    "description": "Id of the client of the contract of the add-on, if applicable",
                    "example": 123,
                    "value": lambda o: o.contract.client.id if o.contract else None
                },
                "note": {
                    "type": "string",
                    "description": "Additional notes added to the add-on",
                    "example": "This add-on has a note",
                    "value": lambda o: o.note
                },
                'contract_event_id': {
                    "description": "The ID of the contract event",
                    "type": "integer",
                    "example": 6,
                    "value": lambda o: o.contract_event.id if o.contract_event else None
                },
                'cash_collection_agent': {
                    "description": "The ID of the agent collecting cash (will mark cash as collecte if provided)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 6,
                    "value": lambda o: o.sale_made_by.id if o.sale_made_by else None
                },
                'delivered': {
                    "type": "boolean",
                    "description": "Boolean flag indicating if the add-on has been delivered",
                    "example": True,
                    "value": lambda o: o.delivered
                },
                'planned_delivery_date': {
                    "description": "The planned delivery date of the add-on",
                    "type": "string",
                    "format": "date-time",
                    "example": "2020-04-03",
                    "value": lambda o: o.derived_planned_delivery_date()
                },
                'delivery_date': {
                    "description": "The delivery date of the add-on",
                    "type": "string",
                    "format": "date-time",
                    "example": "2020-04-03T23:30:34",
                    "value": lambda o: o.delivery_date_with_default()
                },
                'skip_hook': {
                    "description": "If this is set to true, the Lead Edited hook will not be sent as a result of that request (but will still get triggered by future requests). This is typically used to avoid loops of hooks with 3rd party applications.",
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "example": False,
                    "value": None
                }
            },
            "create_required": [],
            "create_allowed": ["offer_code", "offer_id", "offer", "offer_version_id", "lead_id", "lead", "contract_reference", "quantity_sold", "loan_mode", "note", "cash_collection_agent", "device_serial", "approved", "delivered", "skip_hook", "planned_delivery_date"],
            "create_forbidden": [],
            "edit_required": [],
            "edit_allowed": ['quantity_sold', 'offer_version_id', 'offer_code', 'note', 'loan_mode', 'cancelled', 'approved', 'approved_by', 'cash_collection_agent', 'delivered', 'planned_delivery_date', 'skip_hook'],
            "edit_forbidden": [],
            "view_required": [],
            "view_forbidden": ['cash_collection_agent', 'skip_hook'],
            "view_allowed": None,
            "no_docs": ["cash_collection_agent", 'skip_hook']
        }

class AddOnType(TypeClassBase):
    lump_sum = 'Lump-Sum'
    loan = 'Loan Extension'
    loan_duration_change = 'Loan Duration Change'
    deposit_change = 'Deposit Change'

    _NO_VALUE_TYPES = [loan_duration_change, deposit_change]

    _human_codes = {
        lump_sum: 'Lump-Sum',
        loan: 'Loan Value Increase',
        loan_duration_change: 'Loan Duration Change',
        deposit_change: 'Deposit Change'
    }

    _human_codes_new = {
        lump_sum: 'Paid Upfront',
        loan: 'Loan Value Change',
        loan_duration_change: 'Loan Duration Change',
        deposit_change: 'Deposit Change'
    }

    @classmethod
    def _get_human_readable_new(cls, value):
        return cls._human_codes_new.get(value)


class AddOnOfferVersion(db.Entity, ModelDefinitionMixin):
    _table_ = "addonoffer"

    # To be removed after migration, added r_ prefix to avoid these being used unintentionally
    r_name = Optional(str, column="name")
    r_code = Optional(str, column="code")
    r_type = Optional(str, column="type", index=True)
    r_loan_mode = Optional(str, column="loan_mode")
    r_category = Optional(AddOnCategory, column="category")
    r_need_approval = Optional(bool, column="need_approval")
    r_based_on = Optional('AddOnOfferVersion', reverse="r_child_offers", column="based_on")
    r_child_offers = Set('AddOnOfferVersion', reverse='r_based_on')
    r_bundle_items = Set(ContractAddOnBundleItem)
    r_allow_decimal_quantities = Optional(bool, column="allow_decimal_quantities")
    r_entities_allowed_for_leads = Set(OperationalEntity, table="entities_allowed_for_lead_addons")
    r_entities_allowed_for_contracts = Set(OperationalEntity, table="entities_allowed_for_contract_addons")
    # -

    price = Required(Decimal)
    duration_change = Required(Decimal, default=0, scale=4)
    
    available_for_registration = Required(bool, default=True, column="available")
    available_for_sales = Required(bool, default=True, column="pre_sales")

    enforce_extension_limit = Required(bool, default=True)
    contract_add_ons = Set('ContractAddOn')
    modifiedDate = Required(datetime, default=datetime.now, index=True, column="modified_date", volatile=True)
    mobile_uuid = Optional(str, unique=True)
    downpayment = Optional(Decimal)

    version_number = Required(int)
    offer = Required('AddOnOffer')

    def check_data_coherence(self):
        if self.price.normalize().as_tuple()[2] < -2:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')
        if self.offer.type not in [AddOnType.loan, AddOnType.deposit_change] and self.downpayment:
            raise Exception('Not loan extension add-ons cannot have downpayment')

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
        self.check_data_coherence()

    def before_update(self):
        self.check_data_coherence()
        self.modifiedDate = datetime.now()

    # Used for easy access to compute addons
    @property
    def name(self):
        return self.offer.name
    
    @property
    def code(self):
        return self.offer.code
    
    @property
    def offer_type(self):
        return self.offer.type
    
    @property
    def loan_mode(self):
        return self.offer.loan_mode
    
    @property
    def needs_loan_mode(self):
        return self.offer.type in [AddOnType.loan, AddOnType.deposit_change] and not self.offer.loan_mode
    
    @property
    def clean_downpayment(self):
        return self.downpayment or 0 if self.offer.type in [AddOnType.loan, AddOnType.deposit_change] else self.price
    
    @property
    def allow_decimal_quantities(self):
        return self.offer.allow_decimal_quantities
    
    @property
    def linked_to_product(self):
        return self.offer.linked_to_product

    # End of helpers
        
    @property
    def modified_date(self):
        return self.modifiedDate

    @property
    def lead_addons(self):
        return self.contract_add_ons.filter(lambda a: not a.contract)
    
    @property
    def previous_version(self):
        return self.offer.versions.filter(lambda ov: ov.version_number == self.version_number-1).first()
    
    @property
    def changes(self):
        return get_object_changes(self.previous_version, self)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        base_model = {
            "properties": {
                'id': {
                    "description": "The ID of the add-on offer version",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.id,
                    "comparable": False
                },
                'offer_id': {
                    "description": "The ID of the add-on offer",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.offer.id,
                    "comparable": False
                },
                'price': {
                    "description": "The unit price of the offer version",
                    "name": "Price",
                    "oneOf": [{
                        "type": "string",
                        "pattern": MONEY_AMOUNT_PATTERN
                    }, {
                        "type": "number",
                        "format": "float"
                    }],
                    "example": 12.34,
                    "value": lambda o: float(o.price),
                },
                'downpayment': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": MONEY_AMOUNT_PATTERN
                    }, {
                        "type": "number",
                        "format": "float"
                    }],
                    "name": "Downpayment",
                    "example": 6.34,
                    "description": "The amount to be paid as downpayment, if sold to leads",
                    "value": lambda o: o.downpayment,
                },
                'duration_change': {
                    "description": "The duration change per unit added to the loan (in days)",
                    "name": "Duration Change",
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "example": 1,
                    "value": lambda o: float(o.duration_change),
                },
                'available_for_registration': {
                    "description": "If add-ons already created with this version can be registered or approved, could be true (available) or false (unavailable).",
                    "name": "Available for registration",
                    "type": "boolean",
                    "example": False,
                    "value": lambda o: o.available_for_registration
                },
                'available_for_sales': {
                    "type": "boolean",
                    "name": "Available for sales",
                    "description": "If new add-ons can be created with this version, could be true (available) or false (unavailable).",
                    "example": True,
                    "value": lambda o: o.available_for_sales,
                },              
                'enforce_extension_limit': {
                    "type": "boolean",
                    "name": "Enforce addon extension limit",
                    "description": "The enforce addon extension limit of the add-on offer  version for leads, could be true or false.",
                    "example": True,
                    "value": lambda o: o.enforce_extension_limit,
                }
            },
            "create_required": ["offer_id", "price"],
            "create_allowed": [],
            "create_forbidden": ["id"],
            "edit_required": [],
            "edit_allowed": [],
            "edit_forbidden": ["id"],
            "view_required": [],
            "view_allowed": [],
            "view_forbidden": []
        }
        return base_model
            
class AddOnOffer(db.Entity, ModelDefinitionMixin):
    _table_ = "addonofferwrapper"

    name = Required(str)
    code = Required(str)

    type = Required(str, py_check=AddOnType.valid, index=True)
    loan_mode = Optional(str, py_check=AddOnLoanExtensionMode.ovalid)
    
    category = Optional(AddOnCategory, column="category")
    need_approval = Required(bool, default=False)
    
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = Optional(str, unique=True)

    product_type = Optional(str, column="product_type")
    product_sub_type = Optional(ProductSubType, column="product_sub_type")
    linked_to_product = Required(bool, default=False)

    bundle_items = Set(ContractAddOnBundleItem)

    allow_decimal_quantities = Required(bool, default=True)
    purchasing_addon = Required(bool, default=False)

    based_on = Optional('AddOnOffer', reverse="child_offers", column="based_on")
    child_offers = Set('AddOnOffer', reverse='based_on')

    entities_allowed_for_leads = Set(OperationalEntity, table="entities_allowed_for_lead_addons_offers")
    entities_allowed_for_contracts = Set(OperationalEntity, table="entities_allowed_for_contract_addons_offers")

    versions = Set('AddOnOfferVersion')

    def before_update(self):
        self.modifiedDate = datetime.now()

    def is_system(self):
        return self.category and self.category.is_system()
    
    @property
    def modified_date(self):
        return self.modifiedDate

    @property
    def last_version_number(self):
        return orm.max((o.version_number for o in self.versions)) or 0

    @property
    def last_version(self):
        return self.versions.select(lambda o: o.version_number == self.last_version_number).get()
    
    @property
    def version_for_sales(self):
        return self.versions.select(lambda o: o.available_for_sales).get()
    
    @property
    def versions_for_registration(self):
        return self.versions.select(lambda o: o.available_for_registration)

    @property
    def version_for_bundle(self):
        return self.version_for_sales or self.last_version
    
    @property
    def version_number_for_sales(self): # there should be only 1, we use max to transform from a query to a single row
        return orm.max(v.version_number for v in self.versions.select(lambda o: o.available_for_sales))
    
    @property
    def version_for_sales_id(self): # there should be only 1, we use max to transform from a query to a single row
        return orm.max(v.id for v in self.versions.select(lambda o: o.available_for_sales))

    @property
    def is_purchasing_text(self):
        return ' - Purchasing' if self.purchasing_addon else ''
    
    @property
    def name_and_version_for_sales(self):
        return f'{self.name} (v{self.version_number_for_sales}{self.is_purchasing_text})'
    
    @property
    def is_loan(self):
        return self.type == AddOnType.loan
    
    @property
    def lead_addons_count(self):
        return orm.sum(ov.lead_addons.count() for ov in self.versions)
    
    @property
    def addons_count(self):
        return orm.sum(ov.contract_add_ons.count() for ov in self.versions)

    @property
    def is_contract_terms_changes(self):
        return self.type in [AddOnType.deposit_change, AddOnType.loan_duration_change]

    @property
    def changes(self):
        return get_object_changes(self.based_on, self)
    @property
    def is_serialized(self):
        return self.product_sub_type.is_serialized if self.product_sub_type else True # It is serialized if it's just NPG
    
    def can_be_delivered(self):
        return not self.category.is_system() if self.category else True

    def update_bundles(self):
        for bundle in orm.select(b.bundle for b in self.bundle_items):
            bundle.update_cached_data()

    def get_required_device_type(self):
        return self.product_type or None

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        base_model = {
            "properties": {
                'id': {
                    "description": "The ID of the add-on offer",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.id,
                    "comparable": False
                },
                'name': {
                    "description": "The name of the add-on offer",
                    "type": "string",
                    "example": "Example Add-on Offer",
                    "comparable": False,
                    "value": lambda o: o.name
                },
                'code': {
                    "description": "The unique code of the add-on offer",
                    "type": "string",
                    "example": "EXAMPLE_CODE",
                    "comparable": False,
                    "value": lambda o: o.code
                },
                'type': {
                    "description": "The type of the add-on offer",
                    "name": "Type",
                    "type": "string",
                    "enum": AddOnType.to_list(),
                    "value": lambda o: o.type
                },
                'loan_mode': {
                    "name": "Loan Mode",
                    "type": "string",
                    "description": "The type of loan extension",
                    "enum": AddOnLoanExtensionMode.to_list()+ [""],
                    "value": lambda o: o.loan_mode,
                },
                'category': {
                    "description": "The name of the category of the add-on offer",
                    "name": "Category",
                    "type": "string",
                    "example": "Product",
                    "value": lambda o: o.category.name if o.category else None
                },
                'need_approval': {
                    "description": "The approval requirement of the add-on offer, could be true (need to be approved) or false (the add-ons will be automatically approved). Default value is not provided is false.",
                    "type": "boolean",
                    "name": "Approval Required",
                    "example": False,
                    "value": lambda o: o.need_approval
                },
                'allow_decimal_quantities': {
                    "type": "boolean",
                    "name": "Allow decimal quantities",
                    "description": "Allows decimal quantities of the add-on offer, could be true or false.",
                    "example": True,
                    "value": lambda o: o.allow_decimal_quantities,
                },
                'purchasing_addon': {
                    "type": "boolean",
                    "name": "Purchasing addon",
                    "description": "Indicates whether the add-on is a purchasing addon",
                    "example": True,
                    "value": lambda o: o.purchasing_addon,
                },
                'based_on_id': {
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "description": "The ID of the Add-on offer in which this add-on offer is based on.",
                    "example": 12,
                    "comparable": False,
                    "value": lambda o: o.based_on.id if o.based_on else None,
                },
                'disable_base_offer_for_leads': {
                    "type": "boolean",
                    "description": "When creating an offer based on a previous one, this flag indicates whether the base offer should be disabled for sales.",
                    "default": False,
                    "example": True
                },
                'disable_base_offer_for_contracts': {
                    "type": "boolean",
                    "description": "When creating an offer based on a previous one, this flag indicates whether the base offer should be disabled for registration.",
                    "default": False,
                    "example": True
                },
                'replace_base_offer_in_bundles': {
                    "type": "boolean",
                    "description": "When creating an offer based on a previous one, this flag indicates whether the base offer should be replaced by the new one in add-on bundles.",
                    "default": True,
                    "example": True
                },
                'version_for_sales_id': {
                    "description": "The ID of the version of the add-on offer that is available for new sales",
                    "type": "integer",
                    "example": 6,
                    "value": lambda o: o.version_for_sales.id if o.version_for_sales else None
                },
                'versions_for_registration_ids': {
                    "description": "The IDs of the versions of the add-on offer that are available for registration",
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "example": [1,2,3],
                    "value": lambda o: [v.id for v in o.versions_for_registration]
                },
                'product_type': {
                    "description": "The product type of the add-on offer",
                    "type": "string",
                    "example": "AGZ",
                    "value": lambda o: o.product_type if o.product_type else None
                },
                'product_sub_type_id': {
                    "description": "The product sub-type of the add-on offer",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 1,
                    "value": lambda o: o.product_sub_type.id if o.product_sub_type else None
                },
                'linked_to_product': {
                    "description": "Denotes whether the add-on offer required a linked product",
                    "type": "boolean",
                    "example": False,
                    "value": lambda o: o.linked_to_product
                },
            },
            "create_required": ["code", "name", "type"],
            "create_allowed": [],
            "create_forbidden": ["id", "version_for_sales_id"],
            "edit_required": [],
            "edit_allowed": [],
            "edit_forbidden": ["id", "version_for_sales_id"],
            "view_required": [],
            "view_allowed": [],
            "view_forbidden": ["disable_base_offer_for_leads", "disable_base_offer_for_contracts", "replace_base_offer_in_bundles"]
        }
        add_many_to_many_schema(
            base_model,
            "entities_allowed_for_leads",
            "the Operational Entities in which this add-on offer is available for sales",
            "Only leads in these entities can receive add-ons of this offer",
            allow_legacy=True
        )
        add_many_to_many_schema(
            base_model,
            "entities_allowed_for_contracts",
            "the Operational Entities in which this add-on offer is available for registration",
            "Only leads in theses entities can get registered with add-ons of this offer and only contracts in this entities can receive add-ons of this offer",
            allow_legacy=True
        )
        addon_offer_properties = AddOnOfferVersion.get_model_definition(op).get('properties')
        base_model['properties'].update(addon_offer_properties)
        base_model['create_forbidden'] += ['offer_id']
        base_model['view_forbidden'] += [p for p in addon_offer_properties if p != 'id']
        base_model['edit_forbidden'] += [p for p in addon_offer_properties if p != 'id']
        return base_model

    def get_link(self):
        return url_for('contract.view_addon_offer', offer_id=self.id)

    def get_display_id(self):
        return str(self.id)