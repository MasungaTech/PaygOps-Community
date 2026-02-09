from collections import OrderedDict
import copy
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from pony import orm
from datetime import datetime, timedelta
from decimal import Decimal

from core_system.core_entities import db
from payg_loan_system.offers.interfaces import LoanOfferInterface, LumpSumOfferInterface, OfferInterfaces, TimeBasedOfferInterface, UsageBasedOfferInterface
from shared.helpers import date_helper
from shared.helpers.db_helpers import TypeClassBase
from shared.helpers.many_to_many_helpers import add_many_to_many_schema
from shared.logger.loggers import Error
from constants import FLOAT_OPTIONAL_OPTIONS, OFFER_PROPERTIES_INFO, MONTHLY_PAYMENT_FREQUENCY, DAILY_PAYMENT_FREQUENCY, OPTIONAL_STRING_OPTIONS, REQUIRED_FLOAT_OPTIONS, INTEGER_OPTIONAL_OPTIONS
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from shared.services.settings_service import SettingsService


class OfferType(TypeClassBase):
    loan = 'Loan'
    lump_sum = 'Lump Sum'
    time_based = 'Time Based'
    usage_based = 'Usage Based'


class PaymentFrequencyOptions(TypeClassBase):
    daily = DAILY_PAYMENT_FREQUENCY
    monthly = MONTHLY_PAYMENT_FREQUENCY


BASE_OFFER_SCHEMA = OrderedDict({
    "properties": {
        'id': {
            "type": "integer",
            "example": 123,
            "description": "The unique ID of the offer",
            "value": lambda o: o.id
        },
        'based_on': {
            "oneOf": INTEGER_OPTIONAL_OPTIONS,
            "example": 123,
            "description": "If the offer is a new version of an existing offer",
            "value": lambda o: o.parent_offer.id if o.parent_offer else None
        },
        'name': {
            "type": "string",
            "example": "My offer",
            "description": "Descriptive name of the offer, in form of a short text",
            "value": lambda o: o.name
        },
        'code': {
            "type": "string",
            "example": "MY_OFFER_CODE",
            "description": "Unique code to identify the offer, cannot contain spaces",
            "value": lambda o: o.code
        },
        'type': {
            "type": "string",
            "enum": OfferType.to_list(),
            "description": "Discriminator propertiy that defines the rest of the properties being sent/expected",
            "value": lambda o: o.get_human_readable_type_short()
        },
        'linked_to_product': {
            "type": "boolean",
            "example": True,
            "description": "Defines whether the offer should be tied to a device or not",
            "value": lambda o: o.linked_to_product
        },
        'can_be_approved_and_registered': {
            "type": "boolean",
            "example": True,
            "description": "Defines whether the leads can be registered under this offer",
            "value": lambda o: o.in_use
        },
        'in_use_for_new_leads': {
            "type": "boolean",
            "example": True,
            "description": "Defines whether this offer can be assigned to new leads",
            "value": lambda o: o.in_use_for_new_clients
        },
        'approval_required': {
            "type": "boolean",
            "example": True,
            "description": "Defines whether this leads with this offer need to be approved or not",
            "value": lambda o: not o.no_approval_required
        },
        'device_type': {
            "oneOf": OPTIONAL_STRING_OPTIONS,
            "example": "NPG",
            "description": "Restrict the offer to only one specific device type, so leads under this offer cannot be registered with devices of other device type",
            "value": lambda o: o.device_type
        },
        'lighting_global_compliant': {
            "type": "boolean",
            "example": True,
            "description": "Establish wether this offer is compliant with Lighting Global Standards",
            "value": lambda o: o.lighting_global_compliant
        },
        'panel_size_in_w': {
            "oneOf": FLOAT_OPTIONAL_OPTIONS,
            "example": 5.00,
            "description": "The size of the panels in W (if applicable)",
            "value": lambda o: o.panel_size_in_w
        },
        'raw_unit_cost': {
            "oneOf": FLOAT_OPTIONAL_OPTIONS,
            "example": 5.00,
            "description": "The raw cost if the device",
            "value": lambda o: float(o.unit_cost) if o.unit_cost else None
        },
        'battery_size_in_ah': {
            "oneOf": FLOAT_OPTIONAL_OPTIONS,
            "example": 5.00,
            "description": "The battery size of the device (if applicable)",
            "value": lambda o: o.battery_size_in_ah
        },
        'family': {
            "type": "string",
            "enum": ["Home", "Business"],
            "example": "Home",
            "value": lambda o: o.family,
            "description": "Whether the consumer is a home or a business"
        },
        'product_sub_type_id': {
            "description": "The ID of the product sub-type to which this offer is restricted to, if applicable",
            "oneOf": INTEGER_OPTIONAL_OPTIONS,
            "example": 123, 
            "value": lambda o: o.product_sub_type.id if o.product_sub_type else None
        },
        'notes': {
            "type": "string",
            "example": "My extra info about the offer",
            "description": "Additional notes on the offer",
            "value": lambda o: o.notes
        },
        'offline_token_config': {
            "example": {},
            "description": "Configuration for offline token",
        },
        'base_price_amount_can_be_negative': {
            "type": "boolean",
            "example": True,
            "description": "Allows negative base price amount",
            "value": lambda o: o.base_price_amount_can_be_negative
        }
    },
    "create_required": ["name", "code", "type", "approval_required", "family",  "can_be_approved_and_registered", "in_use_for_new_leads", "linked_to_product"],
    "create_allowed": [],
    "create_forbidden": ["id"],
    "edit_required": [],
    "edit_forbidden": ["id"],
    "edit_allowed": [],
    "view_required": [],
    "view_allowed": [],
    "view_forbidden": ['offline_token_config']
})

add_many_to_many_schema(
    BASE_OFFER_SCHEMA,
    "allowed_addon_offer_categories",
    "the allowed Add-ons categories",
    "Only add-ons in offers in this categories can be added to contracts with this offer",
    "addon_offer_categories_allowed"
)

add_many_to_many_schema(
    BASE_OFFER_SCHEMA,
    "entities_allowed_for_leads",
    "the Operational Entities allowed for sales",
    "Only leads in these Operational Entities can be have this offer",
    allow_legacy=True
)

add_many_to_many_schema(
    BASE_OFFER_SCHEMA,
    "entities_allowed_for_contracts",
    "the Operational Entities allowed for registration",
    "Only clients in these Operational Entities can be have this offer on their contracts",
    allow_legacy=True
)

TIME_OFFER_PROPERTIES = {
    'downpayment': {
        "oneOf": FLOAT_OPTIONAL_OPTIONS,
        "example": 10.00,
        "value": lambda o: float(o.registration_fee) if o.registration_fee else None,
        "description": "The amount to be paid as registration fee, before registration"
    },
    'base_price_amount': {
        "oneOf": REQUIRED_FLOAT_OPTIONS,
        "value": lambda o: float(o.base_price_amount) if o.base_price_amount else None,
        "example": 10,
        "description": "The reference amount to be paid in each payment/installment"
    },
    'discount_price_1_amount': {
        "oneOf": FLOAT_OPTIONAL_OPTIONS,
        "value": lambda o: float(o.discount_price_1_amount) if o.discount_price_1_amount else None,
        "example": 20.00,
        "description": "Amount above which the 1st discounted pricing applies"
    },
    'discount_price_2_amount': {
        "oneOf": FLOAT_OPTIONAL_OPTIONS,
        "value": lambda o: float(o.discount_price_2_amount) if o.discount_price_2_amount else None,
        "example": 30.00,
        "description": "Amount above which the 2st discounted pricing applies"
    },
    'minimum_payment': {
        "oneOf": FLOAT_OPTIONAL_OPTIONS,
        "value": lambda o: float(o.minimum_payment) if o.minimum_payment else None,
        "example": 9.00,
        "description": "Minimuma amount accepted to generate a repayment in the contract (and activate device if applicable)"
    },
    'base_price_time_in_days': {
        "oneOf": FLOAT_OPTIONAL_OPTIONS,
        "value": lambda o: int(o.base_price_credit),
        "example": 10.00,
        "description": "Time period equivalent to the reference amount"
    },
    'discount_price_1_time_in_days': {
        "oneOf": FLOAT_OPTIONAL_OPTIONS,
        "value": lambda o: int(o.discount_price_1_credit) if o.discount_price_1_credit else None,
        "example": 22.00,
        "description": "Time period equivalent to the 1st discounted pricing amount"
    },
    'discount_price_2_time_in_days': {
        "oneOf": FLOAT_OPTIONAL_OPTIONS,
        "value": lambda o: int(o.discount_price_2_credit) if o.discount_price_2_credit else None,
        "example": 26.00,
        "description": "Time period equivalent to the 2st discounted pricing amount"
    },
    'time_given_at_start_in_days': {
        "oneOf": FLOAT_OPTIONAL_OPTIONS,
        "value": lambda o: int(o.free_credit_at_start),
        "example": 5.00,
        "description": "Time period given at the beggining of the contract (equivalent to the downpayment amount)"
    },
    "allow_pro_rata": {
        "type": "boolean",
        "default": True,
        "example": True,
        "description": "Defines whether this offer allows payments for arbitrary amounts (higher than the minimum), if true, or only the exact reference/discounted pricing amounts (if false)",
        "value": lambda o: o.allow_pro_rata
    },
    "forgive_lateness": {
        "type": "boolean",
        "default": True,
        "example": True,
        "description": "Defines whether this offer forgives late payments, adding the credit from now (if true) or adding the time from the time when the activation time expired (if false)",
        "value": lambda o: o.forgive_lateness
    },
}

TIME_OFFER_PROPERTIES_CREARTE_REQ = ["downpayment", "base_price_amount"]

class Offer(db.Entity, OfferInterfaces, ModelDefinitionMixin):
    id = orm.PrimaryKey(int, auto=True)

    type = orm.Discriminator(str, py_check=OfferType.valid) # OfferType

    name = orm.Required(str)
    code = orm.Required(str, unique=True)
    family = orm.Required(str)
    parent_offer = orm.Optional('Offer', reverse='child_offers', column='parent_offer')

    in_use = orm.Required(bool, default=True)
    in_use_for_new_clients = orm.Required(bool)

    linked_to_product = orm.Required(bool, default=True)

    entities_allowed_for_leads = orm.Set("OperationalEntity", table="entities_allowed_for_leads_offers")
    entities_allowed_for_contracts = orm.Set("OperationalEntity", table="entities_allowed_for_contracts_offers")

    no_approval_required = orm.Required(bool, default=False)
    automatic_unlock_code_sending = orm.Required(bool, default=False)
    base_price_amount_can_be_negative = orm.Optional(bool)

    # Pricing
    registration_fee = orm.Required(Decimal)
    free_credit_at_start = orm.Required(Decimal, scale=4, default=0)

    allow_pro_rata = orm.Required(bool, default=True)
    forgive_lateness = orm.Required(bool, default=True)

    credit_unit = orm.Optional(str)
    base_price_amount = orm.Required(Decimal, min=0)
    base_price_credit = orm.Required(Decimal, scale=4)
    discount_price_1_amount = orm.Optional(Decimal)
    discount_price_1_credit = orm.Optional(Decimal, scale=4)
    discount_price_2_amount = orm.Optional(Decimal)
    discount_price_2_credit = orm.Optional(Decimal, scale=4)

    # Product Specific
    device_type = orm.Optional(str)
    unit_cost = orm.Optional(Decimal)
    lighting_global_compliant = orm.Optional(bool)
    panel_size_in_w = orm.Optional(int)
    battery_size_in_ah = orm.Optional(int)

    notes = orm.Optional(str)

    addon_offer_categories_allowed = orm.Set("AddOnCategory")
    product_sub_type = orm.Optional('ProductSubType')


    modified_date = orm.Required(datetime, default=datetime.now, index=True, volatile=True)

    # Foreign Key
    entities = orm.Set("HierarchicalOperationalEntity")
    leads = orm.Set('Lead')
    contracts = orm.Set('Contract')
    offer_change_new_offer = orm.Set('ContractEvent')
    offer_change_old_offer = orm.Set('ContractEvent')
    child_offers = orm.Set('Offer', reverse='parent_offer')
    offline_token_configs = orm.Set('OfflineTokenConfig')
    mobile_uuid = orm.Optional(str)
    forms_settings = orm.Set("FormVisibilityRule", table="offer_persondatasurvey")

    def get_link(self):
        from flask import url_for
        return url_for('offers.view_offers', offer_id=self.id)

    def get_display_id(self):
        return str(self.id)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        heirs = {
                'LoanOffer':LoanOffer,
                'LumpSumOffer':LumpSumOffer,
                'TimeBasedOffer':TimeBasedOffer,
                'UsageBasedOffer':UsageBasedOffer
        }
        
        with orm.db_session:
            feature_toggles = SettingsService.get_setting('FeatureToggles')
        if not feature_toggles.get('LumpSumContracts'):
            heirs.pop('LumpSumOffer')
        if not feature_toggles.get('LoanAndSubscriptionContracts'):
            heirs.pop('LoanOffer')
            heirs.pop('TimeBasedOffer')
            heirs.pop('UsageBasedOffer')
        return {
            "heirs": list(heirs.values())
        }

    @property
    def modifiedDate(self):
        return self.modified_date

    @property
    def used(self):
        return bool(
            self.contracts.count() or self.leads.count() or self.offer_change_old_offer.count()
            or self.offer_change_new_offer.count() or self.child_offers.count()
        )

    @property
    def changes(self):
        if not self.parent_offer:
            return {}
        diffs = {}
        for prop in OFFER_PROPERTIES_INFO:
            new = getattr(self, prop, None)
            old = getattr(self.parent_offer, prop, None)
            if new != old:
                if 'formatter' in OFFER_PROPERTIES_INFO[prop]:
                    formatter = OFFER_PROPERTIES_INFO[prop]['formatter']
                    diffs[prop] = [getattr(self, formatter)(new), getattr(self.parent_offer, formatter)(old)]
                elif 'display_func' in OFFER_PROPERTIES_INFO[prop]:
                    disp = OFFER_PROPERTIES_INFO[prop]['display_func']
                    diffs[prop] = [getattr(self, disp)(), getattr(self.parent_offer, disp)()]
                else:
                    diffs[prop] = [new, old]
        return diffs

    @property
    def name_and_code(self):
        return self.name+' - '+self.code

    def check_data_coherence(self):

        if self.minimum_payment and self.minimum_payment > self.base_price_amount:
            raise Error('MINIMUM_PRICE_ABOVE_REFERENCE_PRICE')
        
        if round(self.registration_fee, 2) != self.registration_fee:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')

        if self.minimum_payment and round(self.minimum_payment, 2) != self.minimum_payment:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')
            
        if round(self.base_price_amount, 2) != self.base_price_amount:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')

        if self.discount_price_1_amount and round(self.discount_price_1_amount, 2) != self.discount_price_1_amount:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')

        if self.discount_price_2_amount and round(self.discount_price_2_amount, 2) != self.discount_price_2_amount:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')

        if self.unit_cost and round(self.unit_cost, 2) != self.unit_cost:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')
        
        if self.discount_price_1_amount:
            if not self.discount_price_1_credit:
                raise Error("INVALID_PRICING")
            if self.base_price_amount > self.discount_price_1_amount:
                raise Error("INVALID_PRICING")

        if self.discount_price_2_amount:
            if not self.discount_price_2_credit:
                raise Error("INVALID_PRICING")
            if not self.discount_price_1_amount:
                raise Error("INVALID_PRICING")
            if self.base_price_amount > self.discount_price_2_amount or \
                    self.discount_price_1_amount > self.discount_price_2_amount:
                raise Error("INVALID_PRICING")

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
        self.check_data_coherence()

    def before_update(self):
        self.check_data_coherence()
        self.modified_date = date_helper.getCurrentUtcDate()

    @property
    def is_loan(self):
        return self.type == OfferType.loan

    @property
    def is_lump_sum(self):
        return self.type == OfferType.lump_sum

    @property
    def is_monthly(self):
        return self.type == OfferType.time_based and self.payment_frequency == MONTHLY_PAYMENT_FREQUENCY
        
    @property
    def can_be_completed(self):
        return self.type not in [OfferType.time_based, OfferType.usage_based]

    def add_credit(self, base, credit):
        return base + timedelta(days=float(credit))
    
    def format_credit(self, credit):
        return str(round(credit)) + ' days' if credit else '-'

    # DO NOT USE THIS FOR INTERNAL COMPUTING, IT IS JUST CONVENIENT FOR ANALYTICAL DB
    def reference_payment_frequency_days(self):
        return None

    def get_credit_unit(self):
        return ''

class MinimumPriceOffer(Offer):
    minimum_payment = orm.Optional(Decimal, min=0)


class LoanOffer(MinimumPriceOffer, LoanOfferInterface):
    _discriminator_ = OfferType.loan
    allow_loan_addons = orm.Required(bool, default=True)
    time_to_ownership_in_days = orm.Required(Decimal, scale=4)
    maximum_value_extension = orm.Optional(Decimal, min=0)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        definition = copy.deepcopy(BASE_OFFER_SCHEMA)
        definition.update({
            "title": "Loan Offer"
        })
        definition['properties'].update({
            'time_to_ownership_in_days': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "example": 200.00,
                "value": lambda o: int(o.time_to_ownership_in_days),
                "description": "Total time duration of the contract if paid using the reference pricing"
            },
            'automatic_unlock_code_sending': {
                "type": "boolean",
                "example": True,
                "value": lambda o: o.automatic_unlock_code_sending,
                "description": "Weather to automatically unlock the device forever when finishing contract"
            },
            'allow_loan_addons': {
                "type": "boolean",
                "example": True,
                "value": lambda o: o.allow_loan_addons,
                "description": "Weather loans addons are allowed or not"
            },
            'maximum_value_extension': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: o.maximum_value_extension,
                "example": 200.00,
                "description": "The maximum allowed value of loan extension with loan extension add-ons. "
            },
        })
        definition['properties'].update(TIME_OFFER_PROPERTIES)
        definition['properties']['type'].update({"const": OfferType.loan, "example": OfferType.loan})
        del definition['properties']['type']['enum']
        definition['create_required'] += TIME_OFFER_PROPERTIES_CREARTE_REQ + ["time_to_ownership_in_days", "automatic_unlock_code_sending", "base_price_time_in_days", "time_given_at_start_in_days"]
        return definition

    @property
    def total_maximum_extended(self):
        return self.maximum_value_extension + self.get_total_value_with_deposit()

    @property
    def total_percentage_extended(self):
        return round(self.maximum_value_extension/self.get_total_value_with_deposit()*100, 2)

    def reference_payment_frequency_days(self):
        return self.base_price_credit

    def get_credit_unit(self):
        return 'Days'


class LumpSumOffer(Offer, LumpSumOfferInterface):
    _discriminator_ = OfferType.lump_sum
    allow_loan_addons = False
    minimum_payment = None

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        definition = copy.deepcopy(BASE_OFFER_SCHEMA)
        definition.update({
            "title": "Lump-sum Offer"
        })
        definition['properties'].update({
            'base_price_amount_lump_sum': {
                "oneOf": REQUIRED_FLOAT_OPTIONS,
                "example": 100.00,
                "value": lambda o: float(o.base_price_amount) if o.base_price_amount else None,
                "description": "Total price of the offer"
            }
        })
        definition['properties']['type'].update({"const": OfferType.lump_sum, "example": OfferType.lump_sum})
        del definition['properties']['type']['enum']
        definition['create_required'] += ["base_price_amount_lump_sum"]
        return definition


class TimeBasedOffer(MinimumPriceOffer, TimeBasedOfferInterface):
    _discriminator_ = OfferType.time_based
    payment_frequency = orm.Optional(str, py_check=PaymentFrequencyOptions.ovalid)
    payment_day_of_month = orm.Optional(int, min=1, max=31)
    allow_loan_addons = False

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        definition = copy.deepcopy(BASE_OFFER_SCHEMA)
        definition.update({
            "title": "Time Based Offer"
        })
        definition['properties'].update({
            'payment_frequency': {
                "type": "string",
                "value": lambda o: o.payment_frequency or PaymentFrequencyOptions.daily,
                "enum": PaymentFrequencyOptions.to_list(),
                "description": "Whether the payments schedule will be defined in natural months or in days"
            },
            'base_price_time_in_months': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: int(o.base_price_credit) if o.payment_frequency == PaymentFrequencyOptions.monthly else None,
                "example": 1,
                "description": "Time period equivalent to the reference amount (to be used only if `payment_frequency` is monthly)"
            },
            'discount_price_1_time_in_months': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: int(o.discount_price_1_credit) if o.discount_price_1_credit and o.payment_frequency == PaymentFrequencyOptions.monthly else None,
                "example": 1,
                "description": "Time period equivalent to the 1st discounted pricing amount (to be used only if `payment_frequency` is monthly)"
            },
            'discount_price_2_time_in_months': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: int(o.discount_price_2_credit) if o.discount_price_2_credit and o.payment_frequency == PaymentFrequencyOptions.monthly else None,
                "example": 2,
                "description": "Time period equivalent to the 2st discounted pricing amount (to be used only if `payment_frequency` is monthly)"
            },
            'time_given_at_start_in_months': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: int(o.free_credit_at_start) if o.payment_frequency == PaymentFrequencyOptions.monthly else None,
                "example": 1,
                "description": "Time period given at the beggining of the contract (equivalent to the downpayment amount) in months (to be used only if `payment_frequency` is monthly)"
            },
            'payment_day_of_month': {
                "oneOf": INTEGER_OPTIONAL_OPTIONS,
                "value": lambda o: o.payment_day_of_month,
                "example": 5,
                "description": "The day of the month on which the payment is due"
            }
        })
        definition['properties'].update(TIME_OFFER_PROPERTIES)
        definition['properties']['type'].update({"const": OfferType.time_based, "example": OfferType.time_based})
        del definition['properties']['type']['enum']
        definition['create_required'] += TIME_OFFER_PROPERTIES_CREARTE_REQ
        return definition

    def add_credit(self, base, credit):
        if self.payment_frequency == PaymentFrequencyOptions.monthly:
            return date_helper.add_months(base, credit)
        return super().add_credit(base, credit)
    
    def format_credit(self, credit):
        return str(round(credit)) + (' months' if self.payment_frequency == PaymentFrequencyOptions.monthly else ' days') if credit else '-'

    def reference_payment_frequency_days(self):
        return (self.base_price_credit * Decimal('30.437')) if self.payment_frequency == PaymentFrequencyOptions.monthly else self.base_price_credit
    
    def get_credit_unit(self):
        return 'Months' if self.payment_frequency == PaymentFrequencyOptions.monthly else 'Days'


class UsageBasedOffer(Offer, UsageBasedOfferInterface):
    _discriminator_ = OfferType.usage_based
    allow_loan_addons = False
    minimum_payment = None

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        definition = copy.deepcopy(BASE_OFFER_SCHEMA)
        definition.update({
            "title": "Usage Based Offer",
        })
        definition['properties'].update({
            'downpayment': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "example": 10.00,
                "value": lambda o: float(o.registration_fee) if o.registration_fee else None,
                "description": "The amount to be paid as registration fee, before registration"
            },
            "allow_pro_rata": {
                "type": "boolean",
                "default": True,
                "example": True,
                "description": "Defines whether this offer allows payments for arbitrary amounts (higher than the minimum), if true, or only the exact reference/discounted pricing amounts (if false)",
                "value": lambda o: o.allow_pro_rata
            },
            'minimum_payment': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: float(o.minimum_payment) if o.minimum_payment else None,
                "example": 9.00,
                "description": "Minimuma amount accepted to generate a repayment in the contract (and activate device if applicable)"
            },
            'free_credit_at_start_usage_based': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: float(o.free_credit_at_start) if o.free_credit_at_start else None,
                "example": 10.00,
                "description": "Credit given at the beggining of the contract (equivalent to the downpayment amount)"
            },
            'credit_unit': {
                "type": "string",
                "example": "Liters",
                "value": lambda o: o.credit_unit,
                "description": "Credit units in which the offer is based"
            },
            'base_price_amount': {
                "oneOf": REQUIRED_FLOAT_OPTIONS,
                "value": lambda o: o.base_price_amount,
                "example": 10,
                "description": "The reference amount to be paid"
            },
            'base_price_credit_in_units': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: int(o.base_price_credit),
                "example": 1,
                "description": "Amount if units equivalent to the reference amount"
            },
            'discount_price_1_amount': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: o.discount_price_1_amount,
                "example": 20.00,
                "description": "Amount above which the 1st discounted pricing applies"
            },
            'discount_price_1_credit_in_units': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: o.discount_price_1_credit,
                "example": 2,
                "description": "Amount if units equivalent to `discount_price_1_amount`"
            },
            'discount_price_1_time_in_days': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: o.discount_price_2_credit,
                "example": 3,
                "deprecated": True,
                "description": "Amount if units equivalent to `discount_price_2_amount`"
            },
            'discount_price_2_amount': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: o.discount_price_2_amount,
                "example": 30.00,
                "description": "Amount above which the 2st discounted pricing applies"
            },
            'discount_price_2_credit_in_units': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: o.discount_price_2_credit,
                "example": 3,
                "description": "Amount if units equivalent to `discount_price_2_amount`"
            },
            'discount_price_2_time_in_days': {
                "oneOf": FLOAT_OPTIONAL_OPTIONS,
                "value": lambda o: o.discount_price_2_credit,
                "example": 3,
                "deprecated": True,
                "description": "Amount if units equivalent to `discount_price_2_amount`"
            },
        })
        definition['properties']['type'].update({"const": OfferType.usage_based, "example": OfferType.usage_based})
        del definition['properties']['type']['enum']
        definition['create_required'] += ["downpayment", "free_credit_at_start_usage_based", "credit_unit", "base_price_amount", "base_price_credit_in_units", "discount_price_1_amount", "discount_price_1_credit_in_units", "discount_price_2_amount", "discount_price_2_credit_in_units"]
        return definition

    def format_credit(self, credit):
        return str(round(credit)) + ' ' + self.credit_unit if credit else '-'

    def get_credit_unit(self):
        return self.credit_unit

