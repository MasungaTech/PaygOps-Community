from core_system.phone_numbers.model import PhoneNumbers
from shared.services.settings_service import SettingsService
from datetime import datetime
from shared.logger.loggers import Error


class AddPhoneNumberService:

    @classmethod
    def normalize_phone_number(cls, phone_number):
        if not phone_number:
            return phone_number
        phone_number = phone_number.strip()
        if not phone_number.startswith('+'):
            phone_number = '+'+phone_number
        return phone_number

    @classmethod
    def add_phone_numbers_to_person(cls, phone_number_list, person, validate=True):
        if phone_number_list is None:
            return None
        for phone_number in phone_number_list:
            if phone_number:
                if validate:
                    phone_number = cls.normalize_phone_number(phone_number)
                    cls._is_phone_number_valid(phone_number)
                    cls._check_if_phone_number_owned(phone_number)
                cls._add_phone_number(phone_number, person)

    @classmethod
    def set_preferred_number(cls, preferred_phone_number, person, validate=True):
        if not preferred_phone_number:
            return
        preferred_phone_number = cls.normalize_phone_number(preferred_phone_number)
        this_number = PhoneNumbers.get(number=preferred_phone_number)
        if not this_number:
            if validate:
                cls._is_phone_number_valid(preferred_phone_number)
            this_number = cls._add_phone_number(preferred_phone_number, person)
        else:
            if validate:
                cls._check_if_phone_number_owned_by_other_person(preferred_phone_number, person)
            this_number.persons.add(person)
        person.contactPhone = this_number
        if not person.contactPhone.person or person.contactPhone.person == person:
            person.contactPhone.person = person

    @classmethod
    def _is_phone_number_valid(cls, phone_number):
        EXTENSION = '+' + SettingsService.get_setting('PhoneExtension')
        EXTENSION_LENGTH = len(EXTENSION)
        MAX_LENGTH = EXTENSION_LENGTH + SettingsService.get_setting('PhoneLength')
        MIN_LENGTH = EXTENSION_LENGTH + SettingsService.get_setting('PhoneLengthMin')

        if not phone_number.startswith('+'):
            phone_number = '+'+phone_number # This is added automatically anyway
        if phone_number[:EXTENSION_LENGTH] != EXTENSION:
            raise Error('INVALID_PHONE_NUMBER_EXTENSION', phone_number=phone_number, extension=EXTENSION)

        if len(phone_number) < MIN_LENGTH:
            raise Error('PHONE_NUMBER_TOO_SHORT', phone_number=phone_number, min_length=MIN_LENGTH)

        if len(phone_number) > MAX_LENGTH:
            raise Error('PHONE_NUMBER_TOO_LONG', phone_number=phone_number, max_length=MAX_LENGTH)

        try:
            if '+'+str(int(phone_number)) != phone_number:
                raise Error('PHONE_NUMBER_CONTAINS_SPECIAL_CHARACTERS')
        except Exception as error:
            raise Error('PHONE_NUMBER_CONTAINS_SPECIAL_CHARACTERS')


    @classmethod
    def _add_phone_number(cls, phone_number, person):
        this_number = PhoneNumbers.get(number=phone_number.strip())
        if not this_number:
            this_number = PhoneNumbers(number=phone_number.strip())
        if person:
            this_number.persons.add(person)
            person.modifiedDate = datetime.now()
        return this_number
    
    @classmethod
    def add_phone_number_to_wallet(cls, phone_number, wallet):
        try:
            phone_number = cls.normalize_phone_number(phone_number)
            cls._is_phone_number_valid(phone_number)
        except Error as error:
            return
        this_number = PhoneNumbers.get(number=phone_number.strip())
        if not this_number:
            this_number = PhoneNumbers(number=phone_number.strip())
        wallet.phone_number = this_number
        return this_number

    @classmethod
    def check_phone_numbers(cls, phone_number_list, person=None, reject_if_owned_by_other_person=False):
        if phone_number_list is None:
            return None
        for phone_number in phone_number_list:
            if phone_number:
                phone_number = cls.normalize_phone_number(phone_number)
                cls._is_phone_number_valid(phone_number)
                if reject_if_owned_by_other_person:
                    cls._check_if_phone_number_owned_by_other_person(phone_number, person)
                else:
                    cls._check_if_phone_number_owned(phone_number)

    @classmethod
    def _check_if_phone_number_owned(cls, phone_number):
        this_number = PhoneNumbers.get(number=phone_number.strip())
        if this_number and this_number.persons.select().count() > 0 and not SettingsService.get_setting('AllowMultiplePersonsWithSamePhoneNumber'):
            raise Error('PHONE_NUMBER_ALREADY_OWNED', phone_number=phone_number, person_id=this_number.persons.select().first().id)

    @classmethod
    def _check_if_phone_number_owned_by_other_person(cls, phone_number, person=None):
        this_number = PhoneNumbers.get(number=phone_number.strip())
        if not this_number:
            return
        owner = this_number.persons.select(lambda p: p != person).first()
        legacy_owner = this_number.person if this_number.person and this_number.person != person else None
        owner = owner or legacy_owner
        if owner and not SettingsService.get_setting('AllowMultiplePersonsWithSamePhoneNumber'):
            raise Error('PHONE_NUMBER_ALREADY_OWNED', phone_number=phone_number, person_id=owner.id)

    @classmethod
    def get_phone_owner(cls, phone_number):
        return getattr(PhoneNumbers.get(number=phone_number.strip()), 'person', None)
