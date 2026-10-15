from core_system.person.models.person_entity_change import PersonEntityChange
from payg_loan_system.contracts.models.contract_status import ContractStatus
from constants import FLOAT_PATTERN, INTEGER_PATTERN, BOOLEAN_OPTIONAL_OPTIONS, \
    INTEGER_OPTIONAL_OPTIONS, FLOAT_OPTIONAL_OPTIONS, INTEGER_REQUIRED_OPTIONS, OPTIONAL_STRING_OPTIONS, PICTURE_OPTIONS, REQUIRED_STRING_PATTERN, OPTIONAL_DATETIME_OPTIONS
from datetime import datetime
import random
from pony.orm import select, PrimaryKey, Required, Set, Optional, desc, count, coalesce, sum
from flask import url_for
from core_system.core_entities import db
from payg_loan_system.offers.models import OfferType
from shared.model.interface import ModelInterface
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from core_system.client.services.basic_invidual_client_stat_service import IndividualClientStatService
from core_system.person.services.form_visibility_rule_getter import FormVisibilityRuleGetterService
from payg_loan_system.payments.models.wallet import PaymentWallet, PaymentWalletOwner, PaymentWalletType
import config

ENTERPRISE_FEATURES_ENABLED = getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False)

if ENTERPRISE_FEATURES_ENABLED:
    from after_sales_system.interaction_system.model.interaction_report_model import InteractionMethod
    from after_sales_system.interaction_system.stats.client_stats import getClientAbsentTopic
    from after_sales_system.issue_system.model.issue_model import IssueStatus
    from after_sales_system.notes.model import Note
    from after_sales_system.planning_system.model.interaction_planning_model import InteractionPlan
else:
    InteractionMethod = None
    getClientAbsentTopic = None
    IssueStatus = None
    Note = None
    InteractionPlan = None


class _DisabledQuery:
    """Lightweight stand-in for Pony queries when enterprise models are absent."""

    def __iter__(self):
        return iter(())

    def count(self):
        return 0

    def exists(self):
        return False

    def first(self):
        return None

    def filter(self, *_, **__):
        return self

    def order_by(self, *_, **__):
        return self


DISABLED_QUERY = _DisabledQuery()


class ClientModelInterface(ModelInterface):

    def village_id(self):
        return getattr(self.person.village, 'id', None)

    def get_earliest_payment_due(self):
        return IndividualClientStatService.get_earliest_payment_due(self)

    def get_average_repayment_progression(self, cached=False):
        return IndividualClientStatService.get_average_repayment_progression(self, cached)

    def get_average_timeliness_ratio(self, cached=False):
        return IndividualClientStatService.get_average_timeliness_ratio(self, cached)

    def get_overall_status(self):
        return IndividualClientStatService.get_overall_status(self)

    def get_offer_types(self):
        return [contract.offer.type for contract in self.contracts]


class Client(db.Entity, ClientModelInterface, ModelDefinitionMixin):
    _table_ = 'entrepreneur'
    id = PrimaryKey(int, auto=True)
    person = Required('Person', column='person')

    RegistrationDate = Required(datetime)

    portfolio = Optional('PortfolioEntity', column="portfolio")

    tags = Set("ClientTag")
    Assets = Optional(str)  # Is actually the note

    # FK: Interactions
    payment_wallets = Set(PaymentWallet, cascade_delete=False)
    ActivationRequests = Set("ActivationRequest", cascade_delete=False)
    MentorRequests = Set("MentorRequest", cascade_delete=False)
    if ENTERPRISE_FEATURES_ENABLED:
        note = Set(Note, cascade_delete=False)
        interactionReports = Set('InteractionReport', cascade_delete=False)
        interactionPlans = Set(InteractionPlan, cascade_delete=False)
        issues = Set('Issue', cascade_delete=False)
    transaction_requests = Set('TransactionRequest', cascade_delete=False)
    contracts = Set('Contract', cascade_delete=False)

    destined_stock = Set('StockMovement', cascade_delete=False)
    wallets_owned_history = Set("PaymentWalletOwner", cascade_delete=False)
    forms_answered = Set("SurveyAnswer", cascade_delete=False)
    entity_changes = Set(PersonEntityChange, cascade_delete=False)
    quantity_stock_locations = Set('QuantityStockLocation')

    mobile_uuid = Optional(str, unique=True)

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    eligible_for_new_contract = Required(bool, index=True, volatile=True, default=False)
    # Link to user journey runs only exists in enterprise edition. In OSS mode,
    # keep the FK column as a plain integer so Pony doesn't require the
    # UserJourneyRun entity to exist.
    if ENTERPRISE_FEATURES_ENABLED:
        user_journey_run = Set('UserJourneyRun')
        tasks = Set('Task')

    def before_update(self):
        self.modifiedDate = datetime.now()

    def after_insert(self):
        self.get_cash_account() # We create the cash account from start

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    def tag_added(self):
        self.modifiedDate = datetime.now()

    def preferred_phone_number(self):
        return self.person.contactPhone.number if self.person.contactPhone else None
    
    @property
    def first_active_contract(self):
        return self.active_contracts.first()
    
    @property
    def first_active_or_late_contract(self):
        return self.active_or_late_contracts.first()
    
    @property
    def active_contracts(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.active)
    

    @property
    def active_not_usage_based_contracts(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.active and c.offer.type != OfferType.usage_based)
    

    @property
    def active_or_late_not_usage_based_contracts(self):
        return self.contracts.filter(lambda c: c.status in [ContractStatus.active, ContractStatus.late] and c.offer.type != OfferType.usage_based)

    @property
    def defaulted_contracts(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.defaulted)

    @property
    def cancelled_contracts(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.cancelled)

    @property
    def completed_contracts(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.completed)
    
    @property
    def overpaid_contracts(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.overpaid)
    
    @property
    def paused_contracts(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.paused)

    @property
    def late_contracts(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.late)

    @property
    def active_or_late_contracts(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.active or c.status == ContractStatus.late)
    
    @property
    def defaulted_contracts_with_device(self):
        return self.contracts.filter(lambda c: c.status == ContractStatus.defaulted and c.linked_device != None)

    def update_eligible_for_new_contract(self):
        self.eligible_for_new_contract = self.active_or_late_contracts.count() == 0 and self.person.lead.filter(lambda l: not l.contract and not l.discarded).count() == 0

    @property
    def termination_date(self):
        return select(c.end_time for c in self.contracts).max()
    
    @property
    def last_contract(self):
        return self.contracts.select().order_by(lambda c: desc(c.start_time)).first()
    
    def has_pending_downpayment(self):
        return self.active_contracts.filter(lambda c: not c.downpayment_fully_paid).exists()
    
    def get_total_overpaid(self):
        return sum(r.amount for r in self.person.reconciled_payments.select(lambda rp: not rp.converse))

    def has_contracts_in_status_and_check(self, statuses, check):
        contracts = self.contracts.filter(lambda c: c.status in statuses)
        if check:
            contracts = contracts.filter(check)
        return contracts.exists()

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "This is the ID of the client."
                },
                'name': {
                    "description": "This is the client's first name.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "Name",
                    "value": lambda o: o.person.name
                },
                'surname': {
                    "description": "This is the client's surname.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "Surname",
                    "value": lambda o: o.person.surname
                },
                'birthdate': {
                    "description": "This is the date and time at which the client was born, in ISO 8601 format.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime(1980, 6, 15).isoformat(),
                    "value": lambda o: o.person.birthdate
                },
                'gender': {
                    "description": "This is the client's gender.",
                    "type": "string",
                    "example": list(config.GENDER_NAMES.values())[0],
                    "value": lambda o: o.person.get_gender_name()
                },
                'custom_id': {
                    "description": "This is the custom identifier of the client, if provided.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "A12345678",
                    "value": lambda o: o.person.custom_id
                },
                'preferred_phone_number': {
                    "description": "This is the client's contact phone number including country extension",
                    "type": "string",
                    "format": "phone",
                    "example": "+25534534545",
                    "value": lambda o: o.preferred_phone_number()
                },
                'note': {
                    "description": "This is a note about the client.",
                    "type": "string",
                    "example": "Needs more time to pay",
                    "value": lambda o: o.Assets
                },
                'registration_date': {
                    "description": "This is the date and time at which the client was registered, in ISO 8601 format.",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime(2020, 6, 15).isoformat(),
                    "value": lambda o: o.RegistrationDate
                },
                'gps_longitude': {
                    "description": "This is the longitude of the client",
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "minimum": -180,
                    "maximum": 180,
                    "example": 32.578867,
                    "value": lambda o: o.person.GPSLon
                },
                'gps_latitude': {
                    "description": "This is the latitude of the client",
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "minimum": -90,
                    "maximum": 90,
                    "example": 0.325389,
                    "value": lambda o: o.person.GPSLat
                },
                'picture_id': {
                    "description": "The UUID of the client's picture.",
                    "oneOf": PICTURE_OPTIONS,
                    "example": 'fbdcdefg-0000-aaaa-bbbb-cccc-0123456789ab',
                    "value": lambda o: o.person.profile_picture.uuid if o.person.profile_picture else None
                },
                'village_id': {
                    "description": "The (old) ID of the client's village.",
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }],
                    "example": 12,
                    "deprecated": True,
                    "value": lambda o: o.person.village.not_empty_code
                },
                'l0_entity_id': {
                    "description": "The ID of the client's level-0 entity.",
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }],
                    "example": 12,
                    "value": lambda o: o.person.village.id
                },
                'client_group_id': {
                    "description": "The ID of the client group of the client (if any).",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "value": lambda o: o.person.client_group.id if o.person.client_group else None
                },
                'portfolio_id': {
                    "description": "The ID of the portfolio of the client's active contract (if any of the contracts is active, or the last contract if all are completed).",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 21,
                    "deprecated": True,
                    "value": lambda o: (o.first_active_contract or o.last_contract).portfolio.id if (o.first_active_contract or o.last_contract) and (o.first_active_contract or o.last_contract).portfolio else None
                    # checking (o.first_active_contract or o.last_contract) is needed for old databases with clients without contracts
                },
                'verbal_language': {
                    "description": "The client's spoken language, it can be any arbitrary text.", 
                    "type": "string",
                    "example": "Swahili",
                    "value": lambda o: o.person.verbal_language
                },
                'sms_language': {
                    "description": "The client's language code for SMS. Must be either SW for Swahili, EN for English or FR for French.", 
                    "type": "string",
                    "example": "FR",
                    "value": lambda o: o.person.sms_language
                },
                'next_payment_due_date': {
                    "description": "This is the date and time at which the client's next payment is due (if any), in ISO 8601 format",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime(2021, 3, 20).isoformat(),
                    "value": lambda o: o.get_earliest_payment_due()
                },
                'phone_numbers': {
                    "type": "array",
                    "description": "The phone numbers associated with the client (including the contact phone number)",
                    "items": {
                        "type": "string",
                        "format": "phone"
                    },
                    "example": ["+25534534545", "+25534534546"],
                    "value": lambda o: [p.number for p in o.person.phoneNumbers]
                },
                'contracts': {
                    "type": "array",
                    "description": "The reference of the contracts owned by the client",
                    "items": {
                        "type": "string"
                    },
                    "example": ["C00001", "C00002"],
                    "value": lambda o: [contract.reference for contract in o.contracts]
                },
                'leads': {
                    "type": "array",
                    "description": "The ID of the Leads linked to the client",
                    "items": {
                        "oneOf": INTEGER_REQUIRED_OPTIONS,
                    },
                    "example": [123, 124],
                    "value": lambda o: [lead.id for lead in o.person.lead]
                },
                'form_answers': {
                    "type": "object",
                    "description": "The Form Answer IDs of the answer to different client data forms."
                                   "The details can be obtained with the Form Answer API. ",
                    "example": {
                        "SurveyName": 1
                    },
                    "value": FormVisibilityRuleGetterService.get_client_data_answers_id_for_client
                },
                "tags": {
                    "oneOf": [{
                        "type": "string",
                    }, {
                        "type": "array",
                    }],
                    "example": ["tag1", "tag2", "tag3"],
                    "value": lambda o: [t.name for t in o.tags],
                    "description": "The tags associated with the client. Use `add_tags` and `remove_tags` to modify the tags rather than editing `tags` directly."
                },
                "new_tags": {
                    "type": "string",
                    "example": "tag1, tag2, tag3",
                    "deprecated": True,
                },
                "removed_tags": {
                    "type": "string",
                    "deprecated": True,
                },
                "add_tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "example": ["tag1", "tag2", "tag3"],
                    "description": "Pass tags here to be added to the client. To choose the colour create the tag on the UI before adding it here. ",
                },
                "remove_tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "example": ["tag2", "tag3"],
                    "description": "Pass tags here to be removed to the client.",
                },
                "get_gps_from_picture": {
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "description": "Whether to extract the GPS coordinates from the profila picture or not",
                    "example": True
                },
                "home": {
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "example": True,
                    "description": "If the client is an home client",
                    "value": lambda o: o.person.homeUse
                },
                "business": {
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "description": "If the client is an business client",
                    "example": False,
                    "value": lambda o: o.person.businessUse
                },
                "total_amount_pending_reconciliation": {
                    "type": "number",
                    "description": "The total amount pending reconciliation for the client",
                    "example": 150.75,
                    "value": lambda o: o.get_total_overpaid()
                }
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": ["id", "name", "surname", "registration_date", "birthdate", "gender", "preferred_phone_number", "note", "custom_id", 
                             "registration_date", "gps_longitude", "gps_latitude", "village_id", "l0_entity_id", "client_group_id", "portfolio_id", "verbal_language",
                             "sms_language", "phone_numbers", "picture_id", "tags", "new_tags", "add_tags", "remove_tags", "removed_tags", "get_gps_from_picture", "home", "business"],
            "view_required": ["id", "name", "surname", "registration_date"],
            "view_allowed": None,
            "view_forbidden": ["new_tags", "add_tags", "remove_tags", "removed_tags", "get_gps_from_picture"],
            "no_docs": ["new_tags"]
        }

    @property
    def full_name(self):
        return self.person.full_name

    @property
    def full_name_and_id(self):
        return self.person.full_name + f' (ID: {self.id})'

    @property
    def full_name_and_custom_id(self):
        return self.person.full_name + f' - {coalesce(self.person.custom_id, "")} (ID: {self.id})'

    @property
    def active(self):
        return bool(self.active_or_late_contracts.count() > 0)

    def get_link(self):
        return url_for('client.view_client', client_id=self.id)

    def get_display_id(self):
        return self.person.custom_id or str(self.id)

    def GetDevices(self):
        return select(D for D in db.Device if D.contract.client == self)

    def get_payment_accounts(self):
        payment_accounts = select(A for A in db.PaymentWallet if A.client == self and A.Type != 'Savings')
        return payment_accounts

    def get_cash_account(self):
        cash_account = select(A for A in db.PaymentWallet if A.client.person == self.person and A.Type == PaymentWalletType.cash).first()
        cash_account_lead = select(A for A in db.PaymentWallet if A.lead.person == self.person and A.Type == PaymentWalletType.cash).first()
        cash_account = cash_account if cash_account else cash_account_lead
        if not cash_account:
            full_name = self.person.name + ' ' + self.person.surname + ' (' + str(self.id) + ') [Cash]'
            cash_account = db.PaymentWallet(
                RegistrationDate=datetime.now(),
                FullName=full_name,
                client=self,
                Type=PaymentWalletType.cash,
                operator=''
            )
            PaymentWalletOwner(
                wallet=cash_account,
                client=self,
                date=datetime.now(),
                balance=0
            )
        return cash_account

    def get_user_in_charge(self):
        return self.person.get_user_in_charge()

    def get_average_monthly_visits(self):
        if not ENTERPRISE_FEATURES_ENABLED:
            return 0
        interaction_count = count(I for I in db.InteractionReport if I.client == self
                                 and I.method == InteractionMethod.visit_at_client)  # We remove the install visit
        months = ((self.termination_date or datetime.now())-self.RegistrationDate).days/30
        return interaction_count/months if months else 0

    def get_average_yearly_visits(self):
        if not ENTERPRISE_FEATURES_ENABLED:
            return 0
        interaction_count = count(I for I in db.InteractionReport if I.client == self
                                 and I.method == InteractionMethod.visit_at_client)
        years = ((self.termination_date or datetime.now())-self.RegistrationDate).days/365
        return interaction_count/years if years else 0

    def get_interaction_reports(self):
        if not ENTERPRISE_FEATURES_ENABLED:
            return DISABLED_QUERY
        return select(I for I in db.InteractionReport if I.client == self).order_by(desc(db.InteractionReport.reportDate))

    def get_last_visit_date(self):
        if not ENTERPRISE_FEATURES_ENABLED:
            return None
        clientAbsentTopic = getClientAbsentTopic()
        clientVisits = select(I for I in db.InteractionReport if I.client == self
                              and I.method == InteractionMethod.visit_at_client and I.mainTopic != clientAbsentTopic)
        lastVisit = clientVisits.order_by(desc(db.InteractionReport.reportDate)).first()
        if lastVisit is not None:
            return lastVisit.reportDate
        else:
            return None

    def get_missed_visits_count(self):
        if not ENTERPRISE_FEATURES_ENABLED:
            return 0
        clientAbsentTopic = getClientAbsentTopic()
        clientVisits = select(I for I in db.InteractionReport if I.client == self
                              and I.method == InteractionMethod.visit_at_client and I.mainTopic == clientAbsentTopic)

        return clientVisits.count()

    def getLastPhoneCallDate(self):
        if not ENTERPRISE_FEATURES_ENABLED:
            return None
        clientAbsentTopic = getClientAbsentTopic()
        clientVisits = select(I for I in db.InteractionReport if I.client == self
                              and I.method == InteractionMethod.phone_call and I.mainTopic != clientAbsentTopic)
        lastVisit = clientVisits.order_by(desc(db.InteractionReport.reportDate)).first()
        if lastVisit is not None:
            return lastVisit.reportDate
        else:
            return None

    def getPlannedInteraction(self):
        if not ENTERPRISE_FEATURES_ENABLED:
            return DISABLED_QUERY
        return select(P for P in db.InteractionPlan if P.client == self and not P.disabled and P.interaction is None)

    def hasPlannedInteraction(self):
        planned = self.getPlannedInteraction()
        if planned is DISABLED_QUERY:
            return False
        return planned.count() != 0

    def getOpenIssues(self):
        if not ENTERPRISE_FEATURES_ENABLED:
            return DISABLED_QUERY
        client_issues = select(I for I in db.Issue if I.affectedClient == self)
        return client_issues.filter(lambda I: I.status != IssueStatus.solved
                                    and I.status != IssueStatus.wont_solve)

    def hasOpenIssues(self):
        issues = self.getOpenIssues()
        if issues is DISABLED_QUERY:
            return False
        return issues.count() != 0


class ClientTag(db.Entity, ModelDefinitionMixin):
    name = Required(str, unique=True)
    style = Optional(str)

    clients = Set(Client)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "This is the ID of the tag."
                },
                'name': {
                    "description": "This is the name of the tag. Note that capitalization is ignored for tags.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "Name",
                    "value": lambda o: o.name
                },
                'color': {
                    "description": "This is the color of the tag.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "teal",
                    "enum": config.COLOR_OPTIONS,
                    "value": lambda o: o.style
                }
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': ["name", "color"],
            'create_allowed': [],
            'create_required': []
        }
