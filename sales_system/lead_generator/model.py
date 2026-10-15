from constants import OPTIONAL_STRING_OPTIONS, REQUIRED_STRING_PATTERN, OPTIONAL_DATETIME_OPTIONS
from datetime import datetime
from pony.orm import PrimaryKey, Required, Optional, Set, select
from core_system.core_entities import db
from shared.helpers import date_helper
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from sales_system.lead_generator.services.other_services import LeadGeneratorBaseClass
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from flask import url_for
import config



class LeadGeneratorType(db.Entity, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    name = Required(str, unique=True)
    generators = Set('LeadGenerator')

    @classmethod
    def get_model_definition(cls, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id
                },
                'name': {
                    "description": "The name of the lead generator type, as shown in the label",
                    "type": "string",
                    "pattern": REQUIRED_STRING_PATTERN,
                    "example": "Village Chief",
                    "value": lambda o: o.name
                }
            },
            "create_required": ["name"],
            "create_allowed": ["name"],
            "edit_required": [],
            "edit_allowed": ["name"],
            "view_required": ["id", "name"],
            "view_allowed": []
        }


class LeadGenerator(db.Entity, LeadGeneratorBaseClass, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    person = Required('Person', column="person")
    phoneNumber = Optional(str) # to be removed
    old_type = Optional(str, index=True, column="type") # DEPRECATED
    type = Required('LeadGeneratorType', column="generator_type")
    typicalCommission = Optional(int) # DEPRECATED
    leads = Set('Lead')
    working = Optional(bool, default=True)
    start_date = Required(datetime, default=date_helper.getCurrentUtcDate)

    # Special types, we don't want a reverse attribute so we just add the ID
    MentorID = Optional(int) # DEPRECATED
    ClientID = Optional(int, column='entrepreneurid')

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = Optional(str, unique=True)

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
        
    def before_update(self):
        self.modifiedDate = datetime.now()

    @property
    def full_name(self):
        return self.person.full_name

    @property
    def full_name_and_id(self):
        return f'{self.person.full_name} (ID: {self.id})'

    def get_link(self):
        return url_for('lead_generator.view_lead_generator', generator_id=self.id)

    def get_display_id(self):
        return str(self.id)

    def first_phone_number(self):
        return self.person.phoneNumbers.select().first()

    def getConvertedLeads(self):
        return self.leads.filter(lambda l: l.installed)
    
    def getConvertedLeadsCount(self):
        return self.getConvertedLeads().count()

    def getActiveLeads(self):
        return self.leads.filter(lambda l: l.active)

    def getDiscardedLeads(self):
        return self.leads.filter(lambda l: l.discarded)

    def getWaitingLeads(self):
        return self.leads.filter(lambda l: not l.decision)

    def getFailedClientsCount(self):
        converted_leads = self.getConvertedLeads()
        return converted_leads.filter(lambda l: l.person.client and not l.person.client.active).count()

    def get_average_lead_conversion_time_in_days(self):
        converted_leads = self.getConvertedLeads()
        counter = converted_leads.count()
        if counter == 0:
            return None
        total_time = sum([x.total_seconds() for x in select(l.get_conversion_time() for l in converted_leads)])
        return round(total_time / 3600 / counter, 1)

    def getAverageActivationRatio(self):
        converted_leads = self.getConvertedLeads()
        cached_ratios = select(l.contract.cached_timeliness_ratio for l in converted_leads if l.contract.cached_timeliness_ratio)
        ratios_count = cached_ratios.count()
        return sum(cached_ratios)/ratios_count if ratios_count else None

    def getTotalCommissionDue(self):
        return select(l.commission for l in self.getConvertedLeads() if not l.commission_paid).sum()

    def leads_by_date(self, start_date, end_date):
        return self.leads.select(lambda l: l.statusUpdate >= start_date and
                                 l.statusUpdate <= end_date)

    def seniority_by_month(self):
        time = int(round(((datetime.now() - self.start_date).days / 30), 0))

        return '{}m'.format(time)

    def shop_names(self):
        names = {l.person.shop_name() for l in self.leads if l.person.shop_name()}

        return ' / '.join(sorted(names))

    def is_active(self):
        return self.getActiveLeads().count() > 0

    @classmethod
    def get_model_definition(cls, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id
                },
                'name': {
                    "description": "Required if linked_user_id not specified.",
                    "type": "string",
                    "pattern": REQUIRED_STRING_PATTERN,
                    "example": "Jane",
                    "value": lambda o: o.person.name
                },
                'surname': {
                    "description": "Required if linked_user_id not specified.",
                    "type": "string",
                    "pattern": REQUIRED_STRING_PATTERN,
                    "example": "Doe",
                    "value": lambda o: o.person.surname
                },
                'birthdate': {
                    "description": "This is the date and time at which the person was born, in ISO 8601 format.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime(1980, 6, 15).isoformat(),
                    "value": lambda o: o.person.birthdate
                },
                'gender': {
                    "description": "This is the person's gender.",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": list(config.GENDER_NAMES.values())[0],
                    "value": lambda o: o.person.get_gender_name()
                },
                'phone_numbers': {
                    "type": "array",
                    "description": "The phone numbers associated with the person (including the preferred phone number)",
                    "items": {
                        "type": "string",
                        "format": "phone"
                    },
                    "example": ["+25534534545", "+25534534546"],
                    "value": lambda o: [p.number for p in o.person.phoneNumbers]
                },
                'preferred_phone_number': {
                    "description": "This is the person's preferred phone number including country extension",
                    "type": "string",
                    "format": "phone",
                    "example": "+25534534545",
                    "value": lambda o: o.person.contactPhone.number if o.person.contactPhone else None
                },
                'type': {
                    "description": "The type of Lead Generator. ",
                    "type": "string",
                    "example": "Sales Leader",
                    "value": lambda o: o.type.name
                },
                'working': {
                    "description": "This indicates if the Lead Generator is active or not. (Default: True)",
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.working
                },
                'start_date': {
                    "description": "This is the Lead Generator's start data.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime(2001, 6, 15).isoformat(),
                    "value": lambda o: o.start_date
                },
                'linked_user_id': {
                    "type": "integer",
                    "example": 31,
                    "description": "This is the Lead Generator's linked user. When specified, there is no need to set the name, surname or other values shared between User and Lead Generator and editing those values will also edit them on the user. ",
                    "value": lambda o: o.person.user.id if o.person.user else None
                }
            },
            "create_required": ["type"],
            "create_allowed": ["name", "surname", "birthdate", "gender", "phone_numbers", "preferred_phone_number", "type", "working", "linked_user_id"],
            "edit_required": [],
            "edit_allowed": ["name", "surname", "birthdate", "gender", "phone_numbers", "preferred_phone_number", "type", "working", "linked_user_id"],
            "view_required": ["id", "name", "surname", "type", "working", "start_date"],
            "view_allowed": None
        }
