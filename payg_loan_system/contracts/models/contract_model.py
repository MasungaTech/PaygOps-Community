from payg_loan_system.contracts.models.addons_model import AddOnType, ContractAddOn
from datetime import datetime, timedelta
from payg_loan_system.contracts.models.contract_event_model import ContractEventType
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from payg_loan_system.contracts.services.contract_metric_service import IndividualContractMetricMixin
from core_system.core_entities import db, Json
from pony.orm import PrimaryKey, Required, Optional, Set, select, flush, desc, exists
from payg_loan_system.contracts.models.contract_interfaces import ContractInterfaces
from payg_loan_system.contracts.models.contract_status import INACTIVE_CONTRACT_STATUS, ContractStatus
from payg_loan_system.offers.models import OfferType
from decimal import Decimal
from shared.cache.redis_config import delete_cache_key
from shared.logger.loggers import Error
from constants import CONTRACT_CACHE_KEY_PREFIX
from shared.helpers import date_helper
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from decimal import Decimal
from shared.helpers.form_helpers import value_to_bool
from flask import url_for
import config

from shared.model.billing import BilledItem


def add_if(x, y):
    return x + y if x else None


class Contract(db.Entity, ContractInterfaces, IndividualContractMetricMixin, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    reference = Required(str, index=True, unique=True)
    status = Required(str, default=ContractStatus.active, index=True)
    start_time = Required(datetime, index=True)
    end_time = Optional(datetime, index=True)
    repossession_time = Optional(datetime)
    next_repayment_due_time = Optional(datetime, index=True)
    offer = Required('Offer', column="offer")
    client = Required('Client', column="client")
    lead = Optional('Lead', column='lead')
    linked_device = Optional('Device', column='linked_device')
    portfolio = Optional('PortfolioEntity', column='portfolio')

    # FK
    add_ons = Set('ContractAddOn', cascade_delete=False)
    repayments = Set('ContractRepayment', cascade_delete=False)
    contract_events = Set('ContractEvent', cascade_delete=False)
    pending_reconciled_payment = Set('ReconciledPayment')
    billed_items = Set(BilledItem)

    # Necessary for the update
    modified_date = Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = Optional(str, unique=True)


    # --------- Cached Values ---------
    # Category A - Hook-based compute
    # Update on contract terms changed
    cached_total_value = Optional(Decimal, volatile=True)
    cached_total_downpayment = Optional(Decimal)
    cached_reference_price_increase = Optional(Decimal, volatile=True)
    cached_loan_extension_addon_amount = Optional(Decimal, volatile=True)
    cached_lump_sum_addon_amount = Optional(Decimal, volatile=True)
    cached_total_days_to_ownership = Optional(Decimal, volatile=True)
    cached_expected_payments_table = Optional(Json, lazy=True, volatile=True)

    # Update on repayment received
    cached_cumulative_amount_repaid = Optional(Decimal, volatile=True)
    cached_cumulative_credit_bought = Optional(Decimal, volatile=True)
    cached_cumulative_amount_discounted = Optional(Decimal, volatile=True)
    cached_cumulative_days_in_arrears_until_last_payment = Optional(Decimal, volatile=True)

    # Update on repayment received or contract terms change
    cached_percentage_paid = Optional(Decimal, precision=8, scale=4, index=True, volatile=True)

    # Category B
    # Only needs updating if the date has expired
    cached_expected_amount_repaid = Optional(Decimal, volatile=True)
    cached_expected_amount_repaid_until = Optional(datetime, volatile=True)

    # Category C
    cached_cumulative_days_late = Optional(Decimal, index=True, volatile=True)
    cached_timeliness_ratio = Optional(Decimal, index=True, volatile=True)
    last_time_active = Optional(datetime, index=True)
    last_time_inactive = Optional(datetime, index=True)
    if config.ENABLE_ENTERPRISE_FEATURES:
        tasks = Set('Task')

    PARAMETERS = [
        {
            "name": "include_objects",
            "in": "query",
            "description": "Include information of sub-resources",
            "required": False,
            "schema": {
                "type": "string",
                "enum": ["true", "false", "True", "False"],
                "default": "false",
            },
            "examples": {
                'true': {
                    "value": "true",
                    "summary": "With subobjects"
                },
                'false': {
                    "value": "false",
                    "summary": "Without subobjects"
                }
            },
        }, {
            "name": "special_data",
            "in": "query",
            "description": "Include additional metrics. ",
            "required": False,
            "schema": {
                "type": "string",
                "enum": ["true", "false", "True", "False"],
                "default": "false",
            },
            "examples": {
                'true': {
                    "value": "true",
                    "summary": "With additional metrics"
                },
                'false': {
                    "value": "false",
                    "summary": "Without additional metrics"
                }
            },
        }, {
            "name": "at_time",
            "in": "query",
            "description": "Date-time point at which the metrics should be calculated, if not provided returns current data",
            "required": False,
            "schema": {
                "type": "string",
                "format": "date-time",
                "default": "",
            },
            "examples": {
                'now': {
                    "value": "",
                    "summary": "No time provided, calculated at currrent time"
                },
                'several': {
                    "value": (datetime.now()-timedelta(days=30)).isoformat(),
                    "summary": "Calculated 30 days ago"
                }
            },
        }
    ]

    @property
    def person(self):
        return self.client.person

    def sorted_repayments(self):
        return self.repayments.order_by(lambda r: (r.time, r.id))

    def get_link(self):
        return url_for('contract.view_contract', contract_reference=self.reference)

    def get_display_id(self):
        return self.reference

    @property
    def addons_price(self):
        return select(a.repayment_increase for a in self.add_ons.filter(lambda ad: ad.loan and not ad.excluded_effects)).sum()

    def addons_price_at(self, time=None, cached=False, add_on_id=None, excluded_addon_ids=[]):
        if cached and not time and self.cached_reference_price_increase is not None:
            return self.cached_reference_price_increase
        flush()
        time = time or datetime.now()
        if add_on_id:
            return select(a.repayment_increase for a in self.add_ons \
                          if not a.excluded_effects_at(time) \
                            and a.loan \
                            and a.time_approved <= time \
                            and a.id < add_on_id \
                            and a.id not in excluded_addon_ids
                        ).sum()  
        return select(a.repayment_increase for a in self.add_ons \
                      if not a.excluded_effects_at(time) \
                        and a.loan \
                        and a.time_approved <= time \
                        and a.id not in excluded_addon_ids
                    ).sum()

    @property
    def loan_addons(self):
        return self.add_ons.filter(lambda a: a.offer_version.offer.type in [
            AddOnType.loan, AddOnType.deposit_change
        ])

    @property
    def purchasing_addons(self):
        return self.add_ons.filter(lambda a: a.offer_version.offer.purchasing_addon)

    @property
    def purchasing_addons_amount(self):
        return select(a.total_amount for a in self.purchasing_addons).sum()

    @property
    def loan_addons_downpayments(self):
        return select(a.downpayment for a in self.loan_addons if a.lead and not a.cancelled).sum()

    @property
    def loan_addons_downpayments_paid(self):
        return select(a.already_paid for a in self.loan_addons if a.lead).sum()

    @property
    def downpayment_fully_paid(self):
        return exists(
            r for r in self.repayments if (
                r.discount_type == ContractRepaymentDiscountTypes.downpayment
                and not r.converse
            )
        )

    @property
    def unpaid_addons(self):
        return self.add_ons.filter(lambda a: a.unpaid and not a.pending)

    def get_total_downpayment(self, cached=True):
        if cached and self.cached_total_downpayment:
            return self.cached_total_downpayment
        return (
            self.offer.registration_fee
            + self.loan_addons_downpayments
        )

    def get_total_downpayment_paid(self):
        return self.offer.registration_fee + self.loan_addons_downpayments_paid

    @property
    def minimum_payment(self):
        return self.offer.minimum_payment if self.offer.minimum_payment is not None and self.offer.minimum_payment < self.reference_price else self.reference_price

    def minimum_price_at(self, time=None, cached=False):
        return self.offer_at(time).minimum_payment if self.offer_at(time).minimum_payment is not None and self.offer_at(time).minimum_payment < self.reference_price_at(time, cached) else self.reference_price_at(time, cached)

    def next_payment_price(self, cached=False):
        balance = self.get_outstanding_balance(cached=cached)
        return self.reference_price if (not balance or self.reference_price <= balance) else balance

    @property
    def reference_price(self):
        return self.offer.base_price_amount + self.addons_price

    def reference_price_at(self, time=None, cached=False, add_on_id=None, excluded_addon_ids=[]):
        return self.offer_at(time).base_price_amount + self.addons_price_at(time, cached=cached, add_on_id=add_on_id, excluded_addon_ids=excluded_addon_ids)

    @property
    def discount_price_1(self):
        return add_if(self.offer.discount_price_1_amount, self.addons_price)

    def discount_price_1_at(self, time=None, cached=False):
        return add_if(self.offer_at(time).discount_price_1_amount, self.addons_price_at(time, cached=cached))

    @property
    def discount_price_2(self):
        return add_if(self.offer.discount_price_2_amount, self.addons_price)

    def discount_price_2_at(self, time=None, cached=False):
        return add_if(self.offer_at(time).discount_price_2_amount, self.addons_price_at(time, cached=cached))

    @property
    def pending_reconciled_payments_filtered(self):
        return self.pending_reconciled_payment.filter(lambda r: not r.converse)

    def get_units_from_amount(self, amount, allow_below_minimum=False, time=None):
        if amount < self.reference_price_at(time) and not allow_below_minimum:
            return 0
        bundles = [(self.discount_price_2_at(time) or float('inf'), self.offer_at(time).discount_price_2_credit),
                   (self.discount_price_1_at(time) or float('inf'), self.offer_at(time).discount_price_1_credit),
                   (self.reference_price_at(time), self.offer_at(time).base_price_credit)]
        for bundle in bundles:
            if bundle[0] <= amount:
                if bundle[0] == 0:
                    return 0
                return amount/(bundle[0]/bundle[1])
        if self.reference_price_at(time) == 0:
            return 0
        return amount/(self.reference_price_at(time)/self.offer_at(time).base_price_credit)

    def get_value_of_credit(self, credit, time=None):
        return round(Decimal(credit)*self.reference_price_at(time)/(self.offer_at(time).base_price_credit or Decimal('Infinity')), 2)

    def __repr__(self):
        return f'Contract[{self.id}:{self.reference}]'

    def check_data_coherence(self):
        if self.status not in [ContractStatus.active, ContractStatus.paused, ContractStatus.late, ContractStatus.overpaid] and not self.end_time:
            raise Exception('INCOHERENT_CONTRACT_STATUS_NO_END_TIME')

        if self.offer.type != OfferType.usage_based and self.status == ContractStatus.active and not self.next_repayment_due_time:
            raise Exception('INCOHERENT_CONTRACT_STATUS_NO_NEXT_DUE')
        
    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
        self.check_data_coherence()

    def before_update(self):
        self.check_data_coherence()
        self.modified_date = date_helper.getCurrentUtcDate()

    def update_cached_data(self, **kwargs):
        from payg_loan_system.contracts.services.contract_cache_service import ContractCacheService
        ContractCacheService.update_contract_cache(self, **kwargs)
        if self.status in INACTIVE_CONTRACT_STATUS:
            self.last_time_inactive = datetime.now()
        else:
            self.last_time_active = datetime.now()

    def after_update(self):
        cache_key = CONTRACT_CACHE_KEY_PREFIX + str(self.id)
        delete_cache_key(cache_key)
        self.client.update_eligible_for_new_contract()

    @property
    def reference_and_name(self):
        return self.reference+' - '+self.client.full_name

    @property
    def can_be_completed(self):
        return self.offer.can_be_completed

    @property
    def can_be_late(self):
        return (not self.usage_based and not self.lump_sum)

    @property
    def usage_based(self):
        return self.offer.type == OfferType.usage_based

    @property
    def time_based(self):
        return self.offer.type == OfferType.time_based

    @property
    def loan(self):
        return self.offer.type == OfferType.loan

    @property
    def lump_sum(self):
        return self.offer.type == OfferType.lump_sum

    @property
    def pending_amount(self):
        return select(p.amount for p in self.pending_reconciled_payments_filtered).sum()

    @property
    def modifiedDate(self):
        return self.modified_date

    @property
    def contract_terms_cache_update_needed(self):
        # DO NOT REFACTOR: This is written as a one liner way to be compilable by Pony into SQL
        return (self.cached_lump_sum_addon_amount == None) \
            or (self.cached_total_days_to_ownership == None) \
            or (self.can_be_completed and self.cached_expected_payments_table == None) \
            or (self.can_be_completed and self.cached_total_value == None) \
            or (self.offer.type == OfferType.loan and self.cached_reference_price_increase == None) \
            or (self.offer.type == OfferType.loan and self.cached_loan_extension_addon_amount == None)

    @property
    def contract_repayment_cache_update_needed(self):
        # DO NOT REFACTOR: This is written as a one liner way to be compilable by Pony into SQL
        return (self.cached_cumulative_amount_repaid == None) \
            or (self.cached_cumulative_amount_discounted == None) \
            or (self.can_be_completed and self.cached_percentage_paid == None) \
            or (self.can_be_late and self.cached_cumulative_days_in_arrears_until_last_payment == None)

    @property
    def expected_paid_cache_update_needed(self):
        return (not self.usage_based and self.cached_expected_amount_repaid_until == None) \
            or (self.cached_expected_amount_repaid_until != None \
                and self.cached_expected_amount_repaid_until < datetime.now())
    
    @property
    def has_delivered_addon_device(self):
        # Check if the contract has any add-ons linked to a device
        for addon in self.add_ons:
            if addon.device and addon.delivered:
                return True
        return False
    @property
    def has_not_delivered_addon_device(self):
        # Check if the contract has any add-ons linked to a device and if any of those add-ons are not delivered
        for addon in self.add_ons:
            if not addon.delivered and not addon.cancelled and not addon.pending:
                return True
        return False

    def paused_duration(self):
        most_recent_pause_event = self.contract_events.filter(lambda e: e.type == ContractEventType.pause).order_by(lambda e: desc(e.time)).first()
        most_recent_resume_event = self.contract_events.filter(lambda e: e.type == ContractEventType.resume).order_by(lambda e: desc(e.time)).first()
        if most_recent_pause_event and most_recent_resume_event:
            if most_recent_resume_event > most_recent_pause_event:
                return most_recent_resume_event.time - most_recent_pause_event.time
        return timedelta(0)

    @classmethod
    def get_model_definition(cls, op, include_objects=None, special_data=None, at_time=None, **kwargs):
        float_or_none = lambda x: float(x) if x else None
        data = {
            "properties": {
                'id': {
                    "description": "The ID of the contract",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.id
                },
                'reference': {
                    "description": "The reference of the Contract",
                    "type": "string",
                    "example": "C1234001",
                    "value": lambda o: o.reference
                },
                'status': {
                    "description": "The status of the Contract",
                    "type": "string",
                    "enum": ContractStatus.to_list(),
                    "example": "Active",
                    "value": lambda o: o.status
                },
                'start_time': {
                    "description": "The Start Time of the Contract",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime(1980, 6, 15).isoformat(),
                    "value": lambda o: o.start_time
                },
                'next_payment_due_time': {
                    "description": "The time at which the next payment is due of the Contract",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime(1980, 6, 15).isoformat(),
                    "value": lambda o: o.get_repayment_due_time(at_time)
                },
                'client_id': {
                    "description": "The ID of the Contract's Client",
                    "type": "integer",
                    "example": 58,
                    "value": lambda o: o.client.id
                },
                'lead_id': {
                    "description": "The ID of the Contract's Lead",
                    "type": "integer",
                    "example": 53,
                    "value": lambda o: o.lead.id if o.lead else None
                },
                'portfolio_id': {
                    "description": "The ID of the Contract's portfolio, if any",
                    "type": "integer",
                    "example": 58,
                    "value": lambda o: o.portfolio.id if o.portfolio else None
                },
                'offer_id': {
                    "description": "The ID of the Contract's Offer",
                    "type": "integer",
                    "example": 3,
                    "value": lambda o: o.offer_at(at_time).id
                },
                'offer_code': {
                    "description": "The code of the Contract's Offer",
                    "type": "string",
                    "example": "TV1",
                    "value": lambda o: o.offer_at(at_time).code
                },
                'linked_device_serial_number': {
                    "description": "The Serial Number of the Contract's Linked Device",
                    "type": "string",
                    "example": 'SOL-1234',
                    "value": lambda o: getattr(o.linked_device, 'composed_serial', None)
                },
                'total_value': {
                    "description": "The total value of the Contract, including loan addons but not lump-sum addons",
                    "type": "float",
                    "example": 1234.56,
                    "value": lambda o: float_or_none(o.get_total_value(at_time, cached=True))
                },
                'total_yearly_value': {
                    "description": "The total yearly value of the Contract for subscriptions",
                    "type": "float",
                    "example": 1234.56,
                    "value": lambda o: float_or_none(o.get_yearly_value(at_time))
                },
                'add_ons': {
                    "description": "List of addons in that contract (use `include_objects` param for include add-ons data)",
                    "type": "array",
                    "example": None,
                    "value": None
                }
            },
            "create_required": [],
            "create_allowed": [],
            "create_forbidden": ["add_ons"],
            "edit_required": [],
            "edit_forbidden": ["add_ons"],
            "edit_allowed": ["portfolio_id"],
            "view_required": ['id', 'reference', 'status', 'start_time', 'client_id', 'offer_id'],
            "view_allowed": None
        }
        special_data = value_to_bool(special_data)
        if special_data:
            last_non_null_time = lambda o: getattr(o.get_last_non_null_repayment(at_time), 'time', None)
            data["properties"].update({
                "cumulative_days_in_arrear": {
                    "description": "The cumulative days late on repayment (including only time late, not in advance), including for the next payment due (if late on it)",
                    "type": "number",
                    "format": "float",
                    "example": 2.34,
                    "value": lambda o: o.get_cumulative_days_in_arrears(at_time)
                },
                "cumulative_amount_in_arrears": {
                    "description": "The amount expected repaid minus the cumulative amount repaid. ",
                    "type": "number",
                    "format": "float",
                    "example": 500,
                    "value": lambda o: o.get_cumulative_amount_in_arrears(at_time, cached=True, include_negative=True)
                },
                "expected_amount_repaid": {
                    "description": "The amount expected repaid if always on time. ",
                    "type": "number",
                    "format": "float",
                    "example": 1500,
                    "value": lambda o: o.get_expected_amount_repaid(at_time, cached=True)
                },
                "cumulative_amount_repaid": {
                    "description": "The amount actually repaid. ",
                    "type": "number",
                    "format": "float",
                    "example": 1000,
                    "value": lambda o: o.get_cumulative_amount_repaid(at_time, cached=True)
                },
                "outstanding_balance": {
                    "description": "Total Value of the contract minus the Cumulative Amount Repaid. Is the remaining amount due in the contract.",
                    "type": "number",
                    "format": "float",
                    "example": 122.34,
                    "value": lambda o: o.get_outstanding_balance(at_time)
                },
                "last_payment_datetime": {
                    "description": "The time in ISO 8601 at which the last payment on the contrat was received",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().isoformat(),
                    "value": last_non_null_time
                },
                "delays_since_last_payment": {
                    "description": "The total delayed time given since the last payment in days",
                    "type": "number",
                    "format": "float",
                    "example": 3.4,
                    "value": lambda o: o.get_delays_given_in_days(time=at_time or datetime.max, from_time=last_non_null_time(o))
                },
                "reference_pricing_amount": {
                    "description": "The Reference Pricing Amount of the contract including modifications from add-ons",
                    "type": "number",
                    "format": "float",
                    "example": 33.4,
                    "value": lambda o: o.reference_price_at(time=at_time)
                },
                "reference_pricing_duration": {
                    "description": "The Reference Pricing Duration (in days) of the contract",
                    "type": "number",
                    "format": "float",
                    "example": 7.4,
                    "value": lambda o: o.offer_at(at_time).base_price_credit
                },
                "expected_maturity_date": {
                    "description": "The Current Expected Maturity Date. The date at which the contract should finish taken into account modifications of offer and add-ons but without delays or lateness.",
                    "type": "string",
                    "format": "date-time",
                    "example": (datetime.now()+timedelta(days=90)).isoformat(),
                    "value": lambda o: o.get_date_of_maturity_without_lateness(at_time)
                },
                "expected_loan_duration": {
                    "description": "The current expected duration in days of the loan taking into account offer modifications and add-ons but without delays or lateness.",
                    "type": "number",
                    "format": "float",
                    "example": 237.4,
                    "value": lambda o: o.get_days_to_pay(at_time)
                },
                "actual_maturity_date": {
                    "description": "The Actual Maturity Date. The date at which the contract would finish taken into account modifications of offer, add-ons, received delays and any lateness in payments.",
                    "type": "string",
                    "format": "date-time",
                    "example": (datetime.now()+timedelta(days=90)).isoformat(),
                    "value": lambda o: o.get_date_of_maturity(at_time)
                },
                "total_lump_sum_add_ons_value": {
                    "description": "The total monetary value of the lump-sum add-ons sold to the contract.",
                    "type": "number",
                    "format": "float",
                    "example": 2000.34,
                    "value": lambda o: o.get_total_value_of_lumpsum_addons(time=at_time)
                },
                "total_delays_given": {
                    "description": "The total delayed time in days",
                    "type": "number",
                    "format": "float",
                    "example": 23.4,
                    "value": lambda o: o.get_total_days_delays_given(time=at_time)
                },
                "total_number_of_repayments_expected": {
                    "description": "The total of repayment expected for the contract, taking into account add-ons and delays",
                    "type": "number",
                    "format": "int",
                    "example": 43,
                    "value": lambda o: o.get_expected_number_of_repayments(cached=True)
                },
                "total_discounted": {
                    "description": "The total amount discounted",
                    "type": "number",
                    "format": "float",
                    "example": 23.4,
                    "value": lambda o: o.get_total_discounted(time=at_time)
                },
                "total_value_without_discounts": {
                    "description": "The total of the contract without the discounts given, i.e. expected amount repaid at the end of the contract",
                    "type": "number",
                    "format": "int",
                    "example": 43,
                    "value": lambda o: float_or_none(o.get_total_value_without_discounts(at_time, cached=True))
                },
            })
        include_objects = value_to_bool(include_objects)
        if not include_objects:
            data["properties"]["add_ons"].update({
                "items": {
                    "type": "string"
                },
                "example": ['C1270016-A0', 'C1270016-A1'],
                "value": lambda o: [a.reference for a in o.add_ons]
            })
            return data
        data["properties"]["add_ons"].update({
            "items": {
                "type": "object"
            },
            "example": [ContractAddOn.get_model_example()],
            "value": lambda o: [a.get_serialized_object() for a in o.add_ons]
        })
        return data
