from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.offers.models import OfferType
from constants import FLOAT_PATTERN, OPTIONAL_MONEY_OPTIONS, INTEGER_PATTERN, BOOLEAN_OPTIONAL_OPTIONS, \
    INTEGER_OPTIONAL_OPTIONS, INTEGER_REQUIRED_OPTIONS, FLOAT_OPTIONAL_OPTIONS, PICTURE_OPTIONS, OPTIONAL_STRING_OPTIONS, REQUIRED_STRING_PATTERN, OPTIONAL_DATETIME_OPTIONS
from payg_loan_system.contracts.models.addons_model import AddOnType
from core_system.person.services.form_visibility_rule_getter import FormVisibilityRuleGetterService
from datetime import datetime
from decimal import Decimal
from pony.orm import PrimaryKey, Required, Optional, Set, select, coalesce, sum, max, db_session, Json
from flask import url_for
from core_system.core_entities import db
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.helpers import date_helper
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from payg_loan_system.payments.models.wallet import PaymentWalletOwner, PaymentWalletType
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_change_history import StatusChangesHistory
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.models.reasons_for_not_buying import ReasonsForNotBuying
from payg_loan_system.contracts.models.addons_model import AddOnType, ContractAddOn
import config
from shared.model.billing import BilledItem
from shared.services.settings_service import SettingsService
from shared.helpers.form_helpers import value_to_bool
from shared.helpers.numbers import float_if_exists
from shared.model.cached_model import CachedModelMixin
import config

def add_if(x, y):
    return x + y if x is not None else None


class Lead(db.Entity, ModelDefinitionMixin, CachedModelMixin):
    id = PrimaryKey(int, auto=True)
    contacted = Required(bool, default=False)
    decision = Required(bool, default=False) # This is ONLY for approval, not other decisions
    person = Required('Person', column="person")
    receptionTime = Required(datetime, index=True)
    statusID = Optional(int, index=True)
    status = Optional(LeadStatus, column="status")
    statusUpdate = Required(datetime)
    nextContact = Optional(datetime)
    status_comment = Optional(str)
    reasons_for_not_buying = Set(ReasonsForNotBuying) # New We store a string of array
    status_changes_history = Set(StatusChangesHistory)
    future_contract_reference = Optional(str, index=True)
    addons = Set("ContractAddOn")
    offer_editing_locked = Required(bool, default=True)


    agreedDeliveryDate = Optional(datetime)
    commission = Optional(int)
    commissionComment = Optional(str)
    commission_paid = Required(bool, default=False)
    contactTime = Optional(datetime)
    decisionMaker = Optional('User', column="decisionmaker")
    decisionTime = Optional(datetime)
    entryDate = Optional(datetime)
    generator = Optional('LeadGenerator', column="generator")
    installUUID = Optional(str) # to be removed
    offer = Optional('Offer', column="offer")
    portfolio = Optional('PortfolioEntity', column="portfolio")
    promisedToPay = Optional(datetime)
    reporter = Optional('User', column="reporter")
    contract = Optional('Contract')
    reconciled_payments = Set('ReconciledPayment')
    payment_wallets = Set("PaymentWallet", cascade_delete=False)
    wallets_owned_history = Set("PaymentWalletOwner")
    paymentRef = Optional(str) # to be removed
    mobile_uuid = Optional(str, unique=True)
    allocated_device = Optional('Device', column="allocated_device", index=True)
    based_on_lead = Optional('Lead', reverse="child_leads", column="based_on_lead", index=True)
    child_leads = Set('Lead', reverse='based_on_lead')
    entity_changes = Set('PersonEntityChange', cascade_delete=False)
    last_time_active = Optional(datetime, index=True)
    last_time_inactive = Optional(datetime, index=True)

    # User journey runs are enterprise-only. In OSS mode, keep the underlying
    # FK column as integers so Pony doesn't require the UserJourneyRun entity.
    if getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False):
        user_journey_run = Set('UserJourneyRun')
    forms_answered = Set("SurveyAnswer")
    billed_items = Set(BilledItem)

    # Custom data
    custom_data = Optional(Json, lazy=True)

    # Cached data
    cached_data = Optional(Json, volatile=True)

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    if config.ENABLE_ENTERPRISE_FEATURES:
        tasks = Set('Task')

    PARAMETERS = [
        {
            "name": "include_objects",
            "description": "Include information of sub-resources",
            "in": "query",
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
            "description": "Include additional metrics. ",
            "in": "query",
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
            "name": "custom_data",
            "in": "query",
            "description": "Include Custom data written by APIs. ",
            "required": False,
            "schema": {
                "type": "string",
                "enum": ["true", "false", "True", "False"],
                "default": "false",
            },
            "examples": {
                'true': {
                    "value": "true",
                    "summary": "With custom data"
                },
                'false': {
                    "value": "false",
                    "summary": "Without custom data"
                }
            },
        }
    ]


    @property
    def full_name(self):
        return self.person.full_name

    @property
    def full_name_and_id(self):
        return f'{self.person.full_name} (ID: {self.id})'

    @property
    def addons_price(self):
        return select(a.repayment_increase for a in self.addons).sum()

    @property
    def reference_price(self):
        return add_if(getattr(self.offer, "base_price_amount", None), self.addons_price)

    @property
    def discount_price_1(self):
        return add_if(getattr(self.offer, "discount_price_1_amount", None), self.addons_price)

    @property
    def discount_price_2(self):
        return add_if(getattr(self.offer, "discount_price_2_amount", None), self.addons_price)

    @property
    def loan_addons(self):
        return self.addons.filter(lambda a: a.offer_version.offer.type in [
            AddOnType.loan, AddOnType.deposit_change
        ])

    @property
    def loan_addons_value(self):
        return select(a.total_amount for a in self.loan_addons).sum()

    @property
    def loan_addons_downpayments(self):
        return select(a.downpayment for a in self.loan_addons).sum()

    @property
    def lump_sum_addons(self):
        return self.addons.select().filter(lambda a: (
            a.offer_version.offer.type == AddOnType.lump_sum
            and not a.offer_version.offer.purchasing_addon
        ))

    @property
    def lump_sum_addons_value(self):
        return select(a.total_amount for a in self.lump_sum_addons).sum()

    @property
    def addons_value(self):
        return select(a.total_amount for a in self.addons).sum()

    @property
    def purchasing_addons(self):
        return self.addons.filter(lambda a: a.offer_version.offer.purchasing_addon)

    @property
    def purchasing_addons_amount(self):
        return select(a.total_amount for a in self.purchasing_addons).sum()

    @property
    def total_extended(self):
        return sum(a.extension_days for a in self.addons)

    @property
    def future_contract_value(self):
        return self.offer.get_total_value_with_deposit() + self.loan_addons_value

    @property
    def future_contract_value_without_deposit(self):
        return (
            self.offer.get_total_value_without_deposit()
            + self.loan_addons_value
            - self.loan_addons_downpayments
        )

    @property
    def future_contract_duration(self):
        return self.offer.time_to_ownership_in_days + self.total_extended

    @property
    def future_contract_time_to_pay(self):
        return self.offer.get_time_to_pay() + self.total_extended

    @property
    def downpayment(self):
        return (
            self.offer.registration_fee
            + self.lump_sum_addons_value
            + self.loan_addons_downpayments
        )

    @property
    def maximum_pending(self):
        return (
            self.future_contract_value
            + self.lump_sum_addons_value
            - self.already_paid
            + self.total_blocked
        )

    @property
    def reconciled_payments_filtered(self):
        return self.reconciled_payments.filter(
            lambda r: not r.converse or r.time <= self.contract.start_time
        )

    @property
    def addons_have_planned_delivery_date(self):
        return any([a.planned_delivery_date for a in self.addons])

    @property
    def not_contract_term_changes_addons(self):
        return self.addons.filter(
            lambda a: a.offer_version.offer.type not in [
                AddOnType.deposit_change, AddOnType.loan_duration_change
            ]
        )

    @property
    def installed(self):
        return self.status.category == "Installed"
    
    def get_link(self):
        return url_for('leads.view_lead', lead_id=self.id)

    def get_display_id(self):
        return self.person.custom_id or str(self.id)

    def get_last_contact(self):
        if self.modifiedDate is not None and str(self.modifiedDate) != "2001-01-01 00:00:00":
            return self.modifiedDate
        else:
            return self.entryDate

    def get_cash_account(self):
        cash_account = select(A for A in db.PaymentWallet if A.lead == self and A.Type == PaymentWalletType.cash).first()
        if not cash_account:
            full_name = self.person.name + ' ' + self.person.surname + ' (L:' + str(self.id) + ') [Cash]'
            cash_account = db.PaymentWallet(
                RegistrationDate=datetime.now(),
                FullName=full_name,
                lead=self,
                Type=PaymentWalletType.cash,
                operator=''
            )
            PaymentWalletOwner(
                wallet=cash_account,
                lead=self,
                date=datetime.now(),
                balance=0
            )
        return cash_account

    def get_next_contact(self):
        if self.nextContact is not None:
            return self.nextContact
        else:
            return ''

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    def after_insert(self):
        self.update_cached_data()

    def before_update(self):
        self.modifiedDate = datetime.now()
        self.update_cached_data()

    def after_update(self):
        if self.person.client:
            self.person.client.update_eligible_for_new_contract()
        if config.TRIGGER_WEBHOOK_AFTER_EDIT:
            add_hook_after_commit(db, 'lead_edited', self.get_serialized_object())

    def update_cached_data(self):
        if not self.cached_data:
            self.cached_data = {}
        self.cached_data['reference_price'] = float_if_exists(self.reference_price)
        self.cached_data['discount_price_1'] = float_if_exists(self.discount_price_1)
        self.cached_data['discount_price_2'] = float_if_exists(self.discount_price_2)
        self.cached_data['already_paid'] = float_if_exists(self.already_paid)
        self.cached_data['downpayment'] = float_if_exists(self.downpayment if self.offer else None)
        self.cached_data['offer_amount'] = float_if_exists(self.offer.get_total_value_with_deposit() if self.offer else None)

    def get_offer(self):
        return self.offer

    def get_number_installments(self):
        if not (self.offer and self.offer.type == OfferType.loan):
            return 0
        total = self.future_contract_value+self.lump_sum_addons_value
        return ((total-self.downpayment)/self.reference_price)

    #to be used in queries
    def get_conversion_time(self):
        return self.person.client.RegistrationDate - self.receptionTime

    def getConversionTime(self):
        if self.installed:
            delta = self.person.client.RegistrationDate - self.receptionTime
            return delta.days*24 + delta.seconds/3600
        return None

    def has_client(self):
        return self.person and self.person.client

    def get_first_device(self):
        if self.has_client():
            return self.contract.linked_device

    @classmethod
    def get_leads_in_portfolio(cls, portfolio_id):
        return cls.select(lambda l: l.portfolio.id == int(portfolio_id))

    def get_filtered_status_change_history(self):
        filtered_list = []
        last = None
        for status in self.status_changes_history.order_by(lambda s: s.date):
            if not last:
                filtered_list.append(status)
            elif status.status != last.status or status.status_comment != last.status_comment:
                filtered_list.append(status)
            last = status
        return filtered_list

    @classmethod
    def get_model_definition(cls, op, include_objects=None, include_subobjects=None, special_data=None, custom_data=None, individual_object=False, **kwargs):
        data = {
            "properties": {
                'id': {
                    "description": "Id number of the lead",
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id
                },
                'name': {
                    "description": "First name of the lead. Required if not creating Lead from client. ",
                    "type": "string", # Do not make required as it breaks the create from client
                    "example": "Name",
                    "value": lambda o: o.person.name
                },
                'surname': {
                    "description": "Family name of the lead. Required if not creating Lead from client. ",
                    "type": "string", # Do not make required as it breaks the create from client
                    "example": "Surname",
                    "value": lambda o: o.person.surname
                },
                'village': {
                    "description": "old Id number of the village to which the lead belongs to. Required if not creating Lead from client. ",
                    "oneOf": INTEGER_REQUIRED_OPTIONS,
                    "deprecated": True,
                    "example": 12,
                    "value": lambda o: o.person.village.not_empty_code
                },
                'l0_entity_id': {
                    "description": "Id number of the level 0 entity to which the lead belongs to. Required if not creating Lead from client. ",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "value": lambda o: o.person.village.id
                },
                'client_group_id': {
                    "description": "Id number of the client group to which the lead belongs to (if any).",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "value": lambda o: o.person.client_group.id if o.person.client_group else None
                },
                'generator': {
                    "description": "The Id number of the lead generator that generated the lead.",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 123,
                    "value": lambda o: o.generator.id if o.generator else None
                },
                'generation_date': {
                    "description": "This is the date and time at which the lead was generated, in ISO 8601 format.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.receptionTime
                },
                'entry_date': {
                    "description": "This is the date and time at which the lead information was introduced into the system, in ISO 8601 format.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.entryDate
                },
                'entry_by_user': {
                    "description": "The Id number of the user that introduced the lead information into the system.",
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.reporter.id if o.reporter else None
                },
                'status': {
                    "description": "The description of the current status of the lead. It must be a valid status defined in the platform.",
                    "oneOf": [
                        {
                            "type": "string"
                        },
                        {
                            "type": "integer"
                        }
                    ] if op != 'view' else [{"type": "string"}],
                    "example": "MyLeadStatus",
                    "value": lambda o: o.status.name
                },
                'status_comment': {
                    "description": "Additional information about the status of the lead. It can be any text or an empty string if not provided.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "Note about the status",
                    "value": lambda o: o.status_comment
                },
                'status_change_date': {
                    "description": "This is the date and time at which the lead status was last changed, in ISO 8601 format.",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.statusUpdate
                },
                'next_contact': {
                    "description": "This is the date and time at which the lead should be contacted again, in ISO 8601 format, or null if not provided.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.nextContact
                },
                'reasons_for_not_buying': {
                    "description": "A list of the applicable reasons for not buying as strings. If no reason for not buying is provided then it will be an empty list. ",
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {
                                "type": "string",
                                "enum": list(config.REASONS_FOR_NOT_BUYING.values())
                            },
                            {
                                "type": "integer",
                                "enum": list(config.REASONS_FOR_NOT_BUYING.keys())
                            }
                        ] if op != 'view' else [{
                            "type": "string",
                            "enum": list(config.REASONS_FOR_NOT_BUYING.values())
                        }],
                    },
                    "example": ["Too expensive for them", "Need to speak to family"],
                    "value": lambda o: [reason.name for reason in o.reasons_for_not_buying]
                },
                'offer': {
                    "description": "The ID number of the offer linked to the lead or null if not provided.",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 13,
                    "value": lambda o: o.offer.id if o.offer else None
                },
                'payment_reference': {
                    "description": "Write-only field to link a payment to the lead by reference. Can be set to 'REFUND_DEPOSIT' to trigger the refund of the lead deposit. ",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "A12345",
                    "deprecated": True,
                },
                'amount': {
                    "description": "Write-only field to set the amount collected in case of cash collection on the lead using the payment reference field as described above. ",
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "example": 123.32,
                    "deprecated": True,
                },
                'home': {
                    "description": "Flag indicating if the lead plans to use the product for home uses. It can be either true or false.",
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "example": False,
                    "value": lambda o: o.person.homeUse
                },
                'business': {
                    "description": "Flag indicating if the lead plans to use the product for business uses. It can be either true or false.",
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "example": True,
                    "value": lambda o: o.person.businessUse
                },
                'gender': {
                    "description": "This is the lead's gender.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": list(config.GENDER_NAMES.values())[0],
                    "value": lambda o: o.person.get_gender_name()
                },
                'birthdate': {
                    "description": "This is the date of birth of the lead, in ISO 8601 format or null if not provided.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime(1980, 2, 10).isoformat(),
                    "value": lambda o: o.person.birthdate
                },
                'custom_id': {
                    "description": "This is the custom identifier of the lead, if provided.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "A12345678",
                    "value": lambda o: o.person.custom_id
                },
                'gps_longitude': {
                    "description": "This is the longitude of the lead",
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "minimum": -180,
                    "maximum": 180,
                    "example": 32.578867,
                    "value": lambda o: o.person.GPSLon
                },
                'gps_latitude': {
                    "description": "This is the latitude of the lead",
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "minimum": -90,
                    "maximum": 90,
                    "example": 0.325389,
                    "value": lambda o: o.person.GPSLat
                },
                'phone_numbers': {
                    "type": "array",
                    "description": "The phone numbers associated with the lead (including the contact phone number)",
                    "items": {
                        "type": "string",
                        "format": "phone"
                    },
                    "example": ["+25534534545", "+25534534546"],
                    "value": lambda o: [number.number for number in o.person.phoneNumbers]
                },
                'preferred_phone_number': {
                    "description": "This is the lead's contact phone number including country extension",
                    "type": "string",
                    "format": "phone",
                    "example": "+25534534545",
                    "value": lambda o: o.person.contactPhone.number if o.person.contactPhone else None
                },
                'promised_to_pay_date': {
                    "description": "This is the date when the lead has promised to pay, in ISO 8601 format or null if not provided.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.promisedToPay
                },
                'planned_delivery_date': {
                    "description": "This is the date when the device delivery is expected, in ISO 8601 format or null if not provided.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.agreedDeliveryDate
                },
                'commission': {
                    "description": "The amount of money paid to the agent in concept of sales commission or null if not provided",
                    "oneOf": OPTIONAL_MONEY_OPTIONS,
                    "example": 150.51,
                    "value": lambda o: o.commission
                },
                'commission_note': {
                    "description": "Additional information about the commission. It can be any text or an empty string if not provided.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "Note about the commission",
                    "value": lambda o: o.commissionComment
                },
                'portfolio': {
                    "description": "The ID of the lead\'s portfolio if any.",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 21,
                    "value": lambda o: o.portfolio.id if o.portfolio else None
                },
                'sms_language': {
                    "description": "The lead\'s language code for SMS. Must be either SW for Swahili, EN for English, FR for French, PT for Portuguese or ES for Spanish.", 
                    "type": "string",
                    "example": "FR",
                    "value": lambda o: o.person.sms_language
                },
                'verbal_language': {
                    "description": "The lead\'s spoken language, it can be any arbitrary text.", 
                    "type": "string",
                    "example": "Swahili",
                    "value": lambda o: o.person.verbal_language
                },
                'future_contract_reference': {
                    "description": "Reference pre-assigned to the lead that will be the reference of the future contract.",
                    "type": "string",
                    "example": "C00001",
                    "value": lambda o: o.future_contract_reference
                },
                'client': {
                    "description": "The ID of the client related to that lead. This can be used to create a Lead from an existing client (in that case the name, surname and village are optional). It is null if the lead was not created from a client and the lead is not installed. ",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 1234,
                    "value": lambda o: o.person.client.id if o.person.client else None
                },
                'contract_reference': {
                    "description": "Reference of the contract. Can be used to create a new lead from a cancelled contract copying the offer and add-ons.",
                    "type": "string",
                    "example": "C00001",
                    "value": lambda o: o.future_contract_reference
                },
                'form_answers': {
                    "type": "object",
                    "description": "The Form Answer IDs of the answer to different lead data forms."
                                   "The details can be obtained with the Form Answer API. ",
                    "example": {
                        "SurveyName": 1
                    },
                    "value": FormVisibilityRuleGetterService.get_lead_data_answers_id_for_lead
                },
                "get_gps_from_picture": {
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "description": "Whether to extract the GPS coordinates from the profila picture or not",
                    "example": True,
                },
                'picture_id': {
                    "description": "The UUID of the lead's picture.",
                    "oneOf": PICTURE_OPTIONS,
                    "example": 'fbdcdefg-0000-aaaa-bbbb-cccc-0123456789ab',
                    "value": lambda o: o.person.profile_picture.uuid if o.person.profile_picture else None
                },
                "offer_editing_locked": {
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "description": "Security lock to avoid unwanted reconciliations and status changes during" + \
                        " offer and add-ons edition for leads with some amount already paid (including fully paids ones)." + \
                        " Set to true to lock the lead and enable the regular lead flow. Set to false to unlock the lead," +\
                        " allowging offer and add-ons edition and preventing the regular lead flow to happen. Remember to" +\
                        " set to false after edition",
                    "example": True,
                    "value": lambda o: o.offer_editing_locked
                },
                'add_ons': {
                    "description": "List of addons in that lead (use `include_objects` param for include add-ons data)",
                    "type": "array",
                    "example": None,
                    "value": None
                },
                'remove_add_ons': {
                    "description": "List of addons ID to be removed.",
                    "type": "array",
                    "example": None,
                    "value": None
                },
                'custom_data': {
                    "description": "Custom Object Data written through API only. You MUST write only sub-objects into the main object and write with your app key starting with the \"app_\". You may not store data at the root of the object. When you edit, only the data from your app key will be replaced. You can always see the data from other apps. The total size limit is 4KB of JSON data per lead. ",
                    "type": "object",
                    "example": {
                        "app_1234": {"mykey": "myvalue", "mykey2": 1234},
                        "app_5678": {"internal_id": 888, "handler": "PX"},
                    },
                    "value": lambda o: o.custom_data
                },
                'skip_hook': {
                    "description": "If this is set to true, the Lead Edited hook will not be sent as a result of that request (but will still get triggered by future requests). This is typically used to avoid loops of hooks with 3rd party applications.",
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "example": False,
                    "value": None
                },
                "allocated_device": {
                    "description": "The Serial Number of the device allocated to the lead, if any",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "NPG-12345",
                    "value": lambda o: o.allocated_device.composed_serial if o.allocated_device else None
                },
                'based_on_lead_id': {
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "description": "The ID of the lead which this lead is based on",
                    "example": 12,
                    "comparable": False,
                    "value": lambda o: o.based_on_lead.id if o.based_on_lead else None,
                },
                'addons_planned_delivery_date': {
                    "description": "This is the date when the addons delivery is expected, in ISO 8601 format or null if not provided.",
                    "type": "object",
                    "properties": {
                        "planned_delivery_date": {
                            "oneOf": OPTIONAL_DATETIME_OPTIONS,
                            "example": datetime.now().isoformat(),
                        },
                    },
                    "value": lambda o: {a.reference: a.planned_delivery_date for a in o.addons if a.planned_delivery_date}
                },
                'schedule_individual_addon_delivery_dates': {
                    "description": "If this is set to false, the delivery date of addons of the lead will be reset.",
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "example": False,
                    "value": None
                },
            },
            "create_required": ['status'],
            "create_allowed": [],
            "create_forbidden": [
                'id', 'add_ons', 'remove_add_ons', "form_answers", "future_contract_reference",
                "amount", "payment_reference", "entry_date", "entry_by_user"
            ],
            "edit_required": [],
            "edit_allowed": [],
            "edit_forbidden": ["id"],
            "view_required": [],
            "view_forbidden": ["get_gps_from_picture", "custom_data", "remove_add_ons", "payment_reference", "amount", "skip_hook", "addons_planned_delivery_date", "schedule_individual_addon_delivery_dates"],
            "view_allowed": None,
            "no_docs": ["amount", "addons_planned_delivery_date", "schedule_individual_addon_delivery_dates", "remove_add_ons"] 
        }
        custom_data = value_to_bool(custom_data)
        if custom_data:
            data["view_forbidden"].remove("custom_data")
        special_data = value_to_bool(special_data)
        if special_data:
            data["properties"].update({
                'downpayment': {
                    "description": "The amount of the downpayment",
                    "type": "number",
                    "example": 12.34,
                    "value": lambda o: o.downpayment if o.offer else None
                },
                'amount_paid': {
                    "description": "The amount already paid towards the downpayment",
                    "type": "number",
                    "example": 12.34,
                    "value": lambda o: o.already_paid
                },
                "reference_pricing_amount": {
                    "description": "The Reference Pricing Amount of the lead\'s future contract including modifications from add-ons",
                    "type": "number",
                    "format": "float",
                    "example": 33.4,
                    "value": lambda o: o.reference_price if o.offer and o.offer.is_loan else None
                },
                "reference_pricing_duration": {
                    "description": "The Reference Pricing Duration (in days) of the lead\'s future contract",
                    "type": "number",
                    "format": "float",
                    "example": 7.4,
                    "value": lambda o: o.offer.base_price_credit if o.offer and o.offer.type not in [OfferType.lump_sum] else None
                },
                "future_contract_value": {
                    "description": "The total value (including loan add-ons and excluding lump-sum addons) of the lead\'s future contract",
                    "type": "number",
                    "format": "float",
                    "example": 7.4,
                    "value": lambda o: o.future_contract_value if o.offer and o.offer.type in [OfferType.loan, OfferType.lump_sum] else None
                },
                "total_lumpsum_addons_value": {
                    "description": "The total value of the lump-sum addons sold to the lead",
                    "type": "number",
                    "format": "float",
                    "example": 7.4,
                    "value": lambda o: o.lump_sum_addons_value
                },
                "free_credit_at_start": {
                    "description": "The number of free credits (or days) given at the begining of the contract",
                    "type": "number",
                    "format": "integer",
                    "example": 7,
                    "value": lambda o: o.offer.free_credit_at_start if o.offer else None
                },
                "total_duration": {
                    "description": "The total duration of the loan contract",
                    "type": "number",
                    "format": "integer",
                    "example": 365,
                    "value": lambda o: o.future_contract_duration if o.offer and o.offer.type not in [OfferType.lump_sum] else None
                },
            })
        include_subobjects = value_to_bool(include_subobjects)
        include_objects = value_to_bool(include_objects)
        if (individual_object and include_objects) or (not individual_object and include_subobjects):
            data["properties"]["add_ons"].update({
                "items": {
                    "type": "object"
                },
                "example": [ContractAddOn.get_model_example()],
                "value": lambda o: [a.get_serialized_object() for a in o.addons]
            })
            return data
        else:
            data["properties"]["add_ons"].update({
                "example": ['C1270016-A0', 'C1270016-A1'],
                "value": lambda o: [a.reference for a in o.addons]
            })
            return data


    @property
    def info_completed(self):
        answered_forms = FormVisibilityRuleGetterService.get_answered_forms_by_lead(self)
        required_forms = FormVisibilityRuleGetterService.get_forms(
            lead=self, required=True, include_offer_list=[self.offer]
        )
        return set(required_forms) <= set(answered_forms)

    @property
    def forms_missing_for_registration(self):
        answered_forms = FormVisibilityRuleGetterService.get_answered_forms_by_lead(self)
        required_forms = FormVisibilityRuleGetterService.get_forms(
            client=True, required=True, include_offer_list=[self.offer]
        )
        return set(required_forms) - set(answered_forms)

    @property
    def already_paid(self):
        return sum(r.amount for r in self.reconciled_payments)

    @property
    def already_paid_not_blocked(self):
        return sum(r.amount for r in self.reconciled_payments if r.type != ReconciledPaymentType.blocked_during_lead_editing)

    @property
    def total_blocked(self):
        return sum(r.amount for r in self.reconciled_payments if r.type == ReconciledPaymentType.blocked_during_lead_editing)

    @property
    def deposit_paid(self):
        return self.installed or (
            self.offer and (
                self.already_paid - self.purchasing_addons_amount
            ) >= coalesce(self.downpayment, Decimal("-1"))
        )

    @property
    def deposit_paid_not_blocked(self):
        return self.already_paid_not_blocked >= self.downpayment

    @property
    def has_payment_information(self):
        return bool(self.reconciled_payments) or self.purchasing_addons.exists()

    @property
    def left_to_pay(self):
        return max(coalesce(self.downpayment, Decimal("-1")) - self.already_paid_not_blocked, 0)

    ## Status Categories
    @property
    def to_be_convinced(self):
        return not self.decision and self.status.category == StatusCategory.to_be_convinced

    @property
    def awaiting_information(self):
        return not self.decision and self.status.category == StatusCategory.awaiting_information

    @property
    def awaiting_decision(self):
        return not self.decision and self.status.category == StatusCategory.awaiting_decision

    @property
    def awaiting_payment(self):
        return self.approved and not self.deposit_paid and not self.cancelled

    @property
    def awaiting_delivery(self):
        return self.decision and self.deposit_paid and self.active and self.offer_editing_locked

    @property
    def can_receive_payment(self):
        return self.status.category in [StatusCategory.awaiting_payment, StatusCategory.awaiting_delivery]

    @property
    def installed(self):
        return bool(self.contract) and not self.cancelled

    @property
    def inactive(self):
        return self.status.category == StatusCategory.inactive

    @property
    def discarded(self):
        return self.status.category == StatusCategory.discarded

    @property
    def approved(self):
        return self.decision and not (self.discarded or self.inactive)
    
    @property
    def cancelled(self):
        return self.contract and self.contract.status == ContractStatus.cancelled

    @property
    def active(self):
        return self.status.category not in [StatusCategory.discarded, StatusCategory.inactive, StatusCategory.installed, StatusCategory.cancelled]

    @property
    def can_edit_offer(self):
        return (self.already_paid == 0 and self.status.category != StatusCategory.installed) or not self.offer_editing_locked

    def get_user_in_charge(self):
        return self.person.get_user_in_charge()

    def generated_by(self, user):
        return self.generator.person == user.person if self.generator else False

    def created_by(self, user):
        return self.reporter == user
