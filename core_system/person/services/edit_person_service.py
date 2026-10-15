from datetime import datetime
import re
from core_system.users.models.user_model import User
from pony import orm
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from shared.file_upload.services.stored_file_service import StoredFileService
from core_system.operational_entities.models import Village
import config
from shared.helpers.date_helper import parse_datetime
from shared.logger.loggers import Error
from core_system.phone_numbers.services.add_phone_number_service import AddPhoneNumberService
from constants import GENDER_IDS
from core_system.phone_numbers.helpers import remove_number
from core_system.person.models.person_model import Person
from shared.helpers.form_helpers import value_to_bool
from shared.services.settings_service import SettingsService
from shared.services.base_service import BaseService


class EditPersonService(BaseService):

    @classmethod
    def validate_data(cls, data, is_user=False):
        data_to_edit = {}

        village = data.get('village_id', data.get('village'))
        if village:
            this_village = Village.get(code=str(village))
            if not this_village:
                this_village = Village.get(id=int(village))
                if not this_village or this_village.code:
                    raise Error('INVALID_VILLAGE_ID')
                data_to_edit['l0_entity_id'] = this_village.id
        l0entity = data.get('l0_entity_id')
        if l0entity:
            this_village = Village.get(id=l0entity)
            if not this_village:
                raise Error('INVALID_VILLAGE_ID')
            data_to_edit['l0_entity_id'] = this_village.id
        
        if 'name' in data:
            cls.validate_required_fields('first_name', data.get('name'), is_user=is_user)
        if 'surname' in data:
            cls.validate_required_fields('surname', data.get('surname'), is_user=is_user)
        gender = data.get('gender')
        if 'gender' in data:
            if(isinstance(gender, str)):
                cls.validate_required_fields('gender', GENDER_IDS.get(gender.lower()), is_user=is_user)
            else:
                cls.validate_required_fields('gender', gender, is_user=is_user)
        if 'birthdate' in data:
            cls.validate_required_fields('birthdate', data.get('birthdate', ''), is_user=is_user)

        phone_numbers = data.get('phone_numbers')
        if phone_numbers:
            for number in phone_numbers:
                if number:
                    AddPhoneNumberService._is_phone_number_valid(number)
        if 'user_id' in data:
            user = User.get(id=data.get('user_id'))
            lead_generator_profile = user.person.leadGenerator
            if lead_generator_profile:
                raise Error('This user has an existing lead generator profile')

        return data_to_edit

    @classmethod
    def _add_from_data_and_user(cls, data, user, is_user=False):
        cls.validate_data(data, is_user=is_user)
        gender = data.get('gender') or 'Unknown'
        if gender:
            gender = GENDER_IDS.get(gender.lower())
        person = Person(name=data.get('name'),
                  surname=data.get('surname'),
                  type=data.get('person_type'),
                  gender=gender,
                  birthdate=data.get('birthdate') or None,
                  GPSLon=data.get('gps_longitude') if ('gps_longitude' in data.keys()) else None,
                  GPSLat=data.get('gps_latitude') if ('gps_latitude' in data.keys()) else None,
                  village=data.get('village', data.get('l0_entity_id', None)),
                  homeUse=data.get('home') if 'home' in data.keys() else False,
                  businessUse=data.get('business') if 'business' in data.keys() else False)
        cls.edit_phone_numbers(person, data, user)
        return person

    @classmethod
    def edit_person_from_data(cls, person, data, edit_phone_numbers=False, user=None, is_user=False):

        data_to_edit = cls.validate_data(data, is_user=is_user)

        if 'name' in data:
            person.name = cls.validate_required_fields('first_name', data.get('name'), is_user=is_user)
        if 'surname' in data:
            person.surname = cls.validate_required_fields('surname', data.get('surname'), is_user=is_user)
        if 'gender' in data:
            gender = data.get('gender')
            if(isinstance(gender, str)):
                person.gender = GENDER_IDS.get(cls.validate_required_fields('gender', gender, is_user=is_user).lower())
            else:
                person.gender = cls.validate_required_fields('gender', gender, is_user=is_user)
        if 'birthdate' in data:
            person.birthdate = parse_datetime(data.get('birthdate')) if cls.validate_required_fields('birthdate', data.get('birthdate', ''), is_user=is_user) else None
        if 'gps_longitude' in data:
            person.GPSLon = cls.validate_required_fields('gps_coordinates', data.get('gps_longitude'), is_user=is_user) or None
            if person.GPSLon and (person.GPSLon < -180 or person.GPSLon > 360):
                raise Error('The coordinates introduced are invalid', code='INVALID_COORDINATES')
        if 'gps_latitude' in data:
            person.GPSLat = cls.validate_required_fields('gps_coordinates', data.get('gps_latitude'), is_user=is_user) or None
            if person.GPSLat and (person.GPSLat < -90 or person.GPSLat > 90):
                raise Error('The coordinates introduced are invalid', code='INVALID_COORDINATES')

        if 'l0_entity_id' in data_to_edit:
            old_entity = person.village
            person.village = data_to_edit['l0_entity_id']
            now = datetime.now()
            user=user.reload()
            if person.client:
                person.client.entity_changes.create(date=now, old_entity=old_entity, new_entity=person.village, user=user)
            for l in person.lead:
                l.entity_changes.create(date=now, old_entity=old_entity, new_entity=person.village, user=user)

        client_group_id = data.get('client_group_id')
        if client_group_id:
            current_id = person.client_group.id if person.client_group else None
            if client_group_id != current_id:
                client_group = ClientGroupGetterService.get_from_user_and_id(user, client_group_id, strict=True)
                person.client_group = client_group
        elif 'client_group_id' in data:
            person.client_group = None
        if 'home' in data:
            person.homeUse = value_to_bool(data.get('home'))
        if 'business' in data:
            person.businessUse = value_to_bool(data.get('business'))
        if 'verbal_language' in data:
            person.verbal_language = cls.validate_required_fields('verbal_language', data.get('verbal_language'), is_user=is_user)

        if 'preferred_sms_language' in data or 'sms_language' in data:
            sms_language = cls.validate_required_fields('preferred_sms_language', data.get('sms_language'), is_user=is_user)
            if sms_language:
                langs = (config.AVAILABLE_USERS_SMS_LANGUAGES
                        if person.user else config.AVAILABLE_CLIENTS_SMS_LANGUAGES)
                if sms_language not in langs:
                    raise Error('INVALID_SMS_LANGUAGE')
                person.sms_language = sms_language
        if 'picture_id' in data:
            picture_uuid = data.get('picture_id', '')
            this_picture = None
            if picture_uuid:
                this_picture = StoredFileService.get_from_uuid(picture_uuid)
            this_picture = cls.validate_required_fields('profile_picture', this_picture, is_user=is_user)
            person.profile_picture = this_picture # Can be none if not required

        get_gps_from_picture = data.get('get_gps_from_picture', '')
        if get_gps_from_picture:
            this_picture = person.profile_picture
            if this_picture and this_picture.available:
                if this_picture.picture_gpslon and this_picture.picture_gpslat:
                    person.GPSLat = this_picture.picture_gpslat
                    person.GPSLon = this_picture.picture_gpslon
        if edit_phone_numbers:
            cls.edit_phone_numbers(person, data, user)
        custom_id = data.get('custom_id')
        if custom_id:
            cls.validate_custom_id(custom_id, person)
            person.custom_id = custom_id or None

    @classmethod
    def edit_phone_numbers(cls, person, data, user):
        all_phone_numbers = data.get('phone_numbers') or data.get('all_phones_list') or []
        preferred_phone_number = data.get('preferred_phone_number') or data.get('number')
        existing_numbers = [p.number for p in person.phoneNumbers]
        to_add = list(filter(lambda p: p not in existing_numbers, all_phone_numbers)) if all_phone_numbers else None
        to_delete = list(filter(lambda p: p not in all_phone_numbers, existing_numbers)) if 'phone_numbers' in data or 'all_phones_list' in data else None 
        if to_add:
            AddPhoneNumberService.add_phone_numbers_to_person(to_add, person)
        if to_delete:
            cls.remove_phone_numbers(to_delete, user, person)
        if preferred_phone_number:
            AddPhoneNumberService.set_preferred_number(preferred_phone_number, person)

    @classmethod
    def remove_phone_numbers(cls, phone_numbers, user, person):
        if not phone_numbers:
            return
        for phone_number in phone_numbers:
            remove_number(phone_number, user, person)

    @classmethod
    def check_new_phone_numbers(cls, person, data, required=False):
        all_phone_numbers = data.get('phone_numbers')
        preferred_phone_number = data.get('preferred_phone_number')
        to_add = list(filter(lambda p: p not in person.phoneNumbers, all_phone_numbers)) if all_phone_numbers else None
        if not to_add and not preferred_phone_number and required:
            raise Error('You need to provide at least one phone number')
        if to_add:
            AddPhoneNumberService.check_phone_numbers(to_add)
        if preferred_phone_number:
            AddPhoneNumberService.check_phone_numbers([preferred_phone_number])

    @classmethod
    def get_human_readable_error(cls, error):
        if 'INVALID_VILLAGE_ID' in str(error):
            return 'Invalid L0 entity ID. '
        if 'INVALID_SMS_LANGUAGE' in str(error):
            return 'Invalid SMS Language. '
        return None

    @classmethod
    def validate_custom_id(cls, value, person=None):
        if not person:
            existing_person = orm.select(person for person in Person if person.custom_id == value).first()
        else:
            existing_person = orm.select(p for p in Person if p.custom_id == value and person != p).first()
        if existing_person:
            if existing_person.is_orphaned:
                existing_person.delete() # We remove the orphaned person
            else:
                cidname = SettingsService.get_setting('CustomId')
                raise Error(f'{cidname} {value} already exists')
        custom_id_format = SettingsService.get_setting('CustomIdFormat')
        if not re.match(custom_id_format, value):
            raise Error(f"{value} does not match pattern {custom_id_format}")

    @classmethod
    def validate_required_fields(cls, field_name, value, is_user=False):
        if is_user:
            return value
        personal_info_settings_obj = SettingsService.get_setting('LeadInfoSettings')
        if personal_info_settings_obj[field_name]['required'] and not value:
            raise Error(f"{field_name} is a required field")
        return value

    @classmethod
    def _int_to_gender(self, gender_code):
        default = 'not_specified'

        options = {
            1: 'male',
            2: 'female',
            3: default,
        }

        return options.get(gender_code) or default
