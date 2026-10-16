from datetime import datetime
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from pony.orm import Required, Optional, Set
from pony import orm
import config
from shared.services.settings_service import SettingsService
from shared.helpers.db_helpers import searchable_text
from shared.model.interface import ModelInterface
from core_system.core_entities import db
from shared.helpers.db_helpers import TypeClassBase


class PersonType(TypeClassBase):
    client = 1
    user = 2
    unknown = 3
    lead = 4
    leadGenerator = 5


class PersonBase(ModelInterface):

    def preferred_phone_number(self):
        if self.contactPhone is not None:
            return self.contactPhone.number
        if self.phoneNumbers:
            return self.phoneNumbers.select().first().number
        if self.leadGenerator and self.leadGenerator.phoneNumber != '':
            return self.leadGenerator.phoneNumber
        return None

    def first_phone_number(self):
        return self.phoneNumbers.order_by(lambda p: p.number).first()

    def getAge(self):
        if self.birthdate:
            today = datetime.now()
            born = self.birthdate
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            return str(age)

    def getType(self):
        person_types = ['None', 'Client', 'User', 'Unknown', 'Lead', 'Lead Generator']
        return person_types[self.type]

    def shop_name(self):
        if self.user:
            return self.user.shop.name
        if self.client and self.village:
            return self.village.parent.parent.name
        return ''

    def get_sms_language_name(self):
        langs = config.LANGUAGES_NAMES
        if SettingsService.get_setting('CustomLanguageName'):
            langs.update({'CU': SettingsService.get_setting('CustomLanguageName')})
        return langs.get(self.sms_language)

    def get_sms_language(self):
        this_person = Person.get(id=self.id)
        if this_person.sms_language:
            return this_person.sms_language
        if this_person.client:
            return SettingsService.get_setting('DefaultSMSClientsLanguage')
        return SettingsService.get_setting('DefaultSMSUsersLanguage')


class Person(db.Entity, PersonBase):
    name = Optional(str)
    surname = Optional(str)
    type = Required(int)  # 1. Client, 2. User, create UserType entity

    client = Optional('Client', cascade_delete=False)
    user = Optional('User', cascade_delete=False)
    leadGenerator = Optional('LeadGenerator', cascade_delete=False)
    homeUse = Optional(bool, default=False)
    businessUse = Optional(bool, default=False)
    village = Optional('Village', reverse='persons', column="village")
    client_group = Optional("ClientGroup", column="client_group")
    location_information = Optional(str)
    GPSLon = Optional(float)
    GPSLat = Optional(float)
    contactPhone = Optional('PhoneNumbers', reverse='personContactPhone', column="contactphone")
    gender = Optional(int)  # 1.Male, 2.Female, 3.Not Specified
    birthdate = Optional(datetime)
    verbal_language = Optional(str)
    sms_language = Optional(str)
    Picture = Optional(str) # OUTDATED
    profile_picture = Optional('StoredFile')
    old_phone_numbers = Set('PhoneNumbers', reverse='person')
    phoneNumbers = Set('PhoneNumbers', reverse='persons')
    lead = Set('Lead', cascade_delete=False)
    surveyAnswered = Set('SurveyAnswer', reverse='personAnswering') # To be removed
    surveyGiven = Set('SurveyAnswer', reverse='interviewer')
    mobile_uuid = Optional(str, unique=True)
    custom_id = Optional(str, unique=True, index=True)
    searchable_name = Optional(str, index=True)

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    cached_reconciled_payments = Set('ReconciledPayment', reverse='cached_person')
    reconciled_payments = Set('ReconciledPayment', reverse='person')
    cached_addons = Set('ContractAddOn', reverse='cached_person')

    aggregated_billed_items = Set('AggregatedBilledItem', reverse="person")

    @property
    def full_name(self):
        return f'{self.name} {self.surname}'

    @property
    def pending_reconciled_payments_filtered(self):
        return self.reconciled_payments.filter(lambda rp: not rp.converse)

    @property
    def is_orphaned(self):
        return self.client is None and self.user is None and self.leadGenerator is None and orm.count(self.lead) == 0

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
        self.searchable_name = searchable_text(self.name + ' ' + self.surname)
        if self.contactPhone and not self.contactPhone in self.phoneNumbers:
            raise Exception('Main phone number not in phone number list')

    def before_update(self):
        self.modifiedDate = datetime.now()
        self.searchable_name = searchable_text(self.name + ' ' + self.surname)
        if self.contactPhone and not self.contactPhone in self.phoneNumbers:
            raise Exception('Main phone number not in phone number list')

    def get_gender_name(self, lower=False):
        gender = config.GENDER_NAMES.get(self.gender, 'Unknown' if not lower else '')
        if lower:
            return gender.lower()
        return gender
    
    def get_user_in_charge(self):
        return self.client_group.user_in_charge if self.client_group else self.village.inherited_user_in_charge
    
    def get_entity(self):
        return self.client_group or self.village
    
    def get_language(self, full=False, web=False):
        language = getattr(self, 'sms_language', None)
        if not language:
            if self.user and not web:
                language = SettingsService.get_setting('DefaultSMSUsersLanguage')
            elif self.user and web:
                language = SettingsService.get_setting('DefaultWebLanguage')
            else:
                language = SettingsService.get_setting('DefaultSMSClientsLanguage')
        if full:
            LANG_DICT = {
                'FR': 'French',
                'EN': 'English'
            }
            return LANG_DICT.get(language)
        return language

    def user_has_special_permission(self, user):
        if self.client:
            if user.can_access('SyncAllCreatedClientsMobile'):
                for lead in self.lead:
                    if lead.created_by(user):
                        return True
            if user.can_access('SyncAllGeneratedClientsMobile'):
                for lead in self.lead:
                    if lead.generated_by(user):
                        return True
        else:
            if user.can_access('ViewCreatedLeads') or user.can_access('SyncAllCreatedLeadsMobile'):
                for lead in self.lead:
                    if lead.created_by(user):
                        return True
            if user.can_access('SyncAllGeneratedLeadsMobile'):
                for lead in self.lead:
                    if lead.generated_by(user):
                        return True
        return False
    
    def get_type(self):
        return PersonType.to_inv_dict().get(self.type)