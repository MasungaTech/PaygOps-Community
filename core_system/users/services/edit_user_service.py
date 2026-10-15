import os
from decimal import Decimal, DecimalException
from email.utils import parseaddr
import re
from core_system.phone_numbers.services.add_phone_number_service import AddPhoneNumberService
from shared.services.settings_service import SettingsService
from shared.services.translation_service import TranslationService

from pony import orm

import config
from accounting_system.accounting_db import Account, AccountingUser
from core_system.core_entities import db
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from core_system.person.models.person_model import Person, PersonType
from core_system.person.services.edit_person_service import EditPersonService
from core_system.role.methods.getters import get_role_from_id
from core_system.role.services import PermissionService
from core_system.users.models.user_model import User
from core_system.users.services.user_getter_service import UserGetterService
from messages_system.services.send_sms import SMSSend
from sales_system.lead_generator.model import LeadGenerator
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.helpers.auth_helper import encode_password, encode_plaintext_password, legacy_sha256
from shared.helpers.form_helpers import datetime_string_to_datetime
from shared.logger.loggers import Error
from shared.services.email_sender import EmailSender
from shared.services.password_generator import PasswordGenerator
from shared.helpers import date_helper
from sales_system.lead_generator.services.lead_generator_edit_service import LeadGeneratorEditService
from sales_system.lead_generator.services.lead_generator_type_service import LeadGeneratorTypeService
from constants import GENDER_IDS
from shared.services.base_service import BaseService


class EditUserService(BaseService):

    NEW_ACCOUNT_EMAIL_TEMPLATE = "<h3>Hello! \n\nWe have successfully created you new account in PaygOps.</h3>" \
                                 "Your user is: <i>{recipient}</i><br>" \
                                 "Your password is: <i>{raw_password}</i><br>" \
                                 "You can now <a href=\"https://{payg_url}\">login</a> into PaygOps with it.<br><br>" \
                                 "The PaygOps Support Team<br>"
    
    EDITED_PASSWORD_TEMPLATE = "<h3>Hello! \n\nWe have successfully generated a new password for your PaygOps account.</h3>" \
                                 "Your user is: <i>{recipient}</i><br>" \
                                 "Your password is: <i>{raw_password}</i><br>" \
                                 "You can now <a href=\"https://{payg_url}\">login</a> into PaygOps with it.<br><br>" \
                                 "The PaygOps Support Team<br>"

    @classmethod
    def add_user(
        cls, current_user, name, surname, username, password, role, hub, organization=None,
        login_expiration_date=None, sms_language=None, verbal_language=None, pin=None,
        lead_generator_type=None, cash_collection_limit=None, autogen_password=False, language=None,
        email=None, preferred_password_communication=None, numbers_data=None,
        birthdate=None, gender=None, api_access_only=None
    ):
        if not password:
            autogen_password = True
        if autogen_password:
            raw_password = PasswordGenerator.generate_password()
            # Match client-side SHA-256 so encode_password below stores a
            # hash that verifies against the browser login form.
            password = legacy_sha256(raw_password)
        this_person = Person(
            name=name,
            surname=surname,
            type=PersonType.user,
            sms_language=sms_language or language or '',
            verbal_language=verbal_language or '',
            birthdate=birthdate or None,
            gender=gender or None
        )
        this_user = User(
            email=email,
            username=username,
            password=encode_password(password),
            person=this_person,
            AuthorizationLevel=role,
            loginExpirationDate=login_expiration_date or None,
            pin=pin or '',
            organization=organization or '',
            cash_collection_limit=cash_collection_limit,
            shop=hub,
            api_access_only=api_access_only
        )
        this_user.roles_in_entities.create(entity=hub)
        if this_user.is_admin():
            this_user.roles_in_entities.create(entity=None)
        orm.flush()
        if lead_generator_type:
            LeadGeneratorEditService.add_from_data_and_user(user=current_user, data={'linked_user_id': this_user.id, 'type': lead_generator_type})
        old_acc = AccountingUser.get(webUserID=this_user.id)
        if old_acc:
            old_acc.delete()
        this_accounting_user = AccountingUser(webUserID=this_user.id)
        Account(type=0, owner=this_accounting_user)
        orm.flush()
        keep_this_to_avoid_a_db_loading_bug = this_user.accountingUserID
        this_user.accountingUserID = int(this_accounting_user.id)
        numbers_data = numbers_data or {}
        phone_numbers_all = numbers_data.get('phone_numbers') or []
        preferred_phone_number = numbers_data.get('preferred_phone_number')
        if preferred_phone_number and not phone_numbers_all:
            phone_numbers_all.append(preferred_phone_number)
        AddPhoneNumberService.add_phone_numbers_to_person(phone_numbers_all, this_user.person)
        EditPersonService.edit_phone_numbers(this_user.person, numbers_data or {}, current_user)
        add_hook_after_commit(db, 'user_created', this_user.get_serialized_object())
        if autogen_password:
            cls._send_password_by_email(this_user, raw_password, preferred_password_communication=preferred_password_communication)
        return this_user

    @classmethod
    def edit_user(cls, user, name, surname, username, password, role, hub, organization=None,
                  login_expiration_date=None, sms_language=None, verbal_language=None, pin=None,
                  bad_login_count=0, cash_collection_limit=None, email=None,
                  birthdate=None, gender=None, autogen_password=None, api_access_only=None):
        user.person.name = name
        user.person.surname = surname
        user.username = username
        user.email = email
        if password:
            user.password = encode_password(password)
        elif autogen_password:
            raw_password = PasswordGenerator.generate_password()
            user.password = encode_plaintext_password(raw_password)
        if gender:
            user.person.gender = gender
        if birthdate:
            user.person.birthdate = birthdate
        if role.id == 1 and (user.email is None or not user.email.endswith('@solarisoffgrid.com')):
            raise Error('CANNOT_ASSIGN_PERMISSION')

        user.AuthorizationLevel = role
        user.pin = pin or ''
        user.shop=hub
        user.bad_login_count = bad_login_count if bad_login_count else 0
        user.loginExpirationDate = login_expiration_date or None
        user.person.sms_language = sms_language or ''
        user.person.verbal_language = verbal_language or ''
        user.organization = organization or ''
        user.cash_collection_limit = cash_collection_limit
        orm.flush()
        add_hook_after_commit(db, 'user_edited', user.get_serialized_object())
        if autogen_password:
            cls._send_password_by_email(user, raw_password, edit=True)
        user.api_access_only = api_access_only
        return user

    @classmethod
    def _add_from_data_and_user(cls, data, user, confirm_password=False):
        cls.validate_data(data=data, current_user=user, confirm_password=confirm_password)
        return cls.edit_user_from_data(user, data)
    
    @classmethod
    def _edit_from_data_and_user(cls, object=None, data=None , user=None, confirm_password=False):
        cls.validate_data(data=data, current_user=user, confirm_password=confirm_password, edited_user=object)
        return cls.edit_user_from_data(user, data, edited_user=object)

    @classmethod
    def edit_user_from_data(cls, current_user, data, edited_user=None):
        role_id = data.get('role_id', edited_user.AuthorizationLevel.id if edited_user else None)
        role = get_role_from_id(role_id)
        hub = cls.get_affected_entity(data, current_user)
        if not 'reference_entity_id' in data and not 'reference_entity_id' in data:
            hub = edited_user.shop if edited_user else None
        name = data.get('name', edited_user.person.name if edited_user else None)
        surname = data.get('surname', edited_user.person.surname if edited_user else None)
        email = data.get('email', edited_user.email if edited_user else None)
        username = data.get('username', edited_user.username if edited_user else None)
        autogen_password = data.get('auto_generate_password', False)
        password = data.get('password', None)
        sms_language = data.get('language', data.get('sms_language', edited_user.person.sms_language if edited_user else None))
        pin = str(data.get('pin', data.get('mobile_pin', '')))
        if pin == '' and edited_user:
            pin = edited_user.pin
        cash_limit = edited_user.cash_collection_limit if edited_user else None
        if 'cash_collection_limit' in data:
            cash_limit = data['cash_collection_limit'] or None # if empty cast to None
        if cash_limit:
            cash_limit = round(Decimal(str(cash_limit)), 2)
        if 'login_expiration_date' in data:
            login_expiration_date = data.get('login_expiration_date')
            if login_expiration_date:
                login_expiration_date = datetime_string_to_datetime(login_expiration_date)
        else:
            login_expiration_date = edited_user.loginExpirationDate if edited_user else None
        numbers_data = cls.get_phone_numbers_data(data)

        gender = data.get('gender')
        if gender:
            gender = GENDER_IDS.get(gender.lower())

        if not edited_user:
            lead_generator_type = data.get('lead_generator_type', None)
            this_user = cls.add_user(
                current_user,
                name=name,
                surname=surname,
                email=email,
                username=username,
                password=password,
                role=role,
                hub=hub,
                gender=gender,
                birthdate=date_helper.parse_datetime(data.get('birthdate')) or None,
                organization=data.get('organization'),
                login_expiration_date=login_expiration_date,
                sms_language=sms_language,
                verbal_language=data.get('verbal_language'),
                pin=pin,
                lead_generator_type=lead_generator_type,
                cash_collection_limit=cash_limit,
                autogen_password=autogen_password,
                numbers_data=numbers_data,
                preferred_password_communication=data.get('preferred_password_communication', '').lower(),
                api_access_only=True if data.get('api_access_only', False) else False
            )
            return this_user
        else:
            bad_login_count = data.get('bad_login_count', edited_user.bad_login_count) \
                if current_user.is_admin() else edited_user.bad_login_count
            cls.edit_user(
                user=edited_user,
                name=name,
                surname=surname,
                username=username,
                gender=gender,
                birthdate=date_helper.parse_datetime(data.get('birthdate')) or None,
                email=email,
                password=password,
                role=role,
                hub=hub,
                organization=data.get('organization', edited_user.organization),
                login_expiration_date=login_expiration_date,
                sms_language=sms_language,
                verbal_language=data.get('verbal_language', edited_user.person.verbal_language),
                pin=pin,
                cash_collection_limit=cash_limit,
                bad_login_count=bad_login_count,
                autogen_password=autogen_password,
                api_access_only=True if data.get('api_access_only', False) else False
            )
            EditPersonService.edit_phone_numbers(edited_user.person, numbers_data, current_user)
            return edited_user

    @classmethod
    def get_phone_numbers_data(cls, data):
        numbers_data = {}
        if 'phone_numbers' in data:
            numbers_data.update({'phone_numbers': data.get('phone_numbers')})
        if 'all_phones_list[]' in data and hasattr(data, 'getlist'):
            numbers_data.update({'phone_numbers': data.getlist('all_phones_list[]')})
        if 'preferred_phone_number' in data or 'phone_number' in data:
            numbers_data.update({'preferred_phone_number': data.get('preferred_phone_number', data.get('phone_number'))})
        return numbers_data

    @classmethod
    def validate_data(cls, data, current_user, confirm_password=False, edited_user=None):
        hub = cls.get_affected_entity(data, current_user)
        if not 'reference_entity_id' in data and not 'reference_entity_id' in data:
            hub = edited_user.shop if edited_user else None
        if not hub:
            raise Error('INVALID_HUB_ID')
        role_id = data.get('role_id', edited_user.AuthorizationLevel.id if edited_user else None)
        role = get_role_from_id(role_id)
        if not role:
            raise Error('INVALID_ROLE_ID')
        only_expiration_date = list(data.keys()) == ['login_expiration_date'] 
        if not only_expiration_date:
            if not PermissionService.allowed_to_change_to_role(current_user, role):
                raise Error('CANNOT_GIVE_ROLE_WITH_MORE_PERMISSIONS')
            if edited_user and not PermissionService.allowed_to_change_to_role(current_user, edited_user.get_role()):
                raise Error('CANNOT_GIVE_ROLE_WITH_MORE_PERMISSIONS')
        username = data.get('username', edited_user.username if edited_user else None)
        if re.search(r"\s", username):
            raise Error('USERNAME_CONTAINS_SPACE', {'username':username})
        if not edited_user:
            if not username:
                raise Error('USERNAME_REQUIRED')
            if UserGetterService.get_by_username(username):
                raise Error('USERNAME_ALREADY_TAKEN')
        else:
            if username != edited_user.username and UserGetterService.get_by_username(username):
                raise Error('USERNAME_ALREADY_TAKEN')
            
        password_confirm = data.get('password_confirm')
        autogen_password = data.get('auto_generate_password', False)
        password = data.get('password', None)
        if password_confirm is not None and password != password_confirm and not autogen_password:
            raise Error('PASSWORD_DO_NOT_MATCH')
        sms_language = data.get('language', data.get('sms_language', edited_user.person.sms_language if edited_user else None))
        if sms_language:
            if sms_language not in config.AVAILABLE_USERS_SMS_LANGUAGES:
                raise Error('INVALID_SMS_LANGUAGE')
        pin = str(data.get('pin', data.get('mobile_pin', '')))
        if pin == '' and edited_user:
            pin = edited_user.pin
        if pin not in ['', None, '0'] and len(pin) != 4:
            raise Error('INVALID_PIN_LENGTH')
        email = data.get('email', edited_user.email if edited_user else None)
        if email and '@' not in parseaddr(email)[1]:
            raise Error('INVALID_EMAIL_FORMAT')
        preferred_password_communication = data.get('preferred_password_communication', 'email').lower()
        if autogen_password and preferred_password_communication == 'email' and not email:
            raise Error('EMAIL_REQUIRED')
        cash_limit = edited_user.cash_collection_limit if edited_user else None
        if 'cash_collection_limit' in data:
            cash_limit = data['cash_collection_limit'] or None # if empty cast to None
        if cash_limit:
            try:
                round(Decimal(str(cash_limit)), 2)
            except (ValueError, TypeError, DecimalException):
                raise Error('INVALID_CASH_AMOUNT')
        
        numbers_data = cls.get_phone_numbers_data(data)
        phone_numbers = numbers_data.get('phone_numbers')
        normalized_phone_numbers = []
        if phone_numbers:
            for number in phone_numbers:
                if number:
                    normalized_phone_numbers.append(AddPhoneNumberService.normalize_phone_number(number))
                    AddPhoneNumberService._is_phone_number_valid(number)
        preferred_phone_number = numbers_data.get('preferred_phone_number')
        number = preferred_phone_number or (phone_numbers[0] if phone_numbers else None)
        if number:  
            AddPhoneNumberService._is_phone_number_valid(number)
        if not edited_user:
            AddPhoneNumberService.check_phone_numbers(
                phone_numbers,
                reject_if_owned_by_other_person=True
            )
            AddPhoneNumberService.check_phone_numbers(
                [preferred_phone_number],
                reject_if_owned_by_other_person=True
            )
        if preferred_phone_number and phone_numbers is not None:
            preferred_phone_number = AddPhoneNumberService.normalize_phone_number(preferred_phone_number)
            if preferred_phone_number not in normalized_phone_numbers:
                raise Error('PREFERRED_PHONE_NOT_IN_PHONE_NUMBERS', phone_number=preferred_phone_number)
        if autogen_password and preferred_password_communication == 'sms' and not number:
            raise Error('The user does not have a phone number')
        if 'lead_generator_type' in data:
            lead_generator_type = data.get('lead_generator_type')
            if not LeadGeneratorTypeService.get_from_user_and_properties(current_user, name=lead_generator_type):
                raise Error(f'Invalid Lead generator type {lead_generator_type}')

    @classmethod
    def get_human_readable_message(cls, error, user=None):
        return cls.get_human_readable_error(error)

    @classmethod
    def get_human_readable_error(cls, error):
        message = 'Unknown error'
        if str(error) == 'INVALID_ROLE_ID':
            message = 'Invalid role selected!'
        if str(error) == 'INVALID_HUB_ID':
            message = 'Invalid hub selected!'
        if str(error) == 'CANNOT_GIVE_ROLE_WITH_MORE_PERMISSIONS':
            message = 'You can not add a user with more permissions than you have.'
        if str(error) == 'USERNAME_ALREADY_TAKEN':
            message = 'Username already taken.'
        if str(error) == 'EMAIL_ALREADY_TAKEN':
            message = 'Email already taken.'
        if str(error) == 'PASSWORD_DO_NOT_MATCH':
            message = 'Passwords do not match'
        if str(error) == 'NO_PASSWORD':
            message = 'No password provided.'
        if str(error) == 'INVALID_SMS_LANGUAGE':
            message = 'Invalid SMS language.'
        if str(error) == 'INVALID_PIN_LENGTH':
            message = 'Invalid pin length.'
        if str(error) == 'INVALID_DATETIME_FORMAT':
            message = 'Invalid date format.'
        if str(error) == 'USERNAME_REQUIRED':
            message = 'The username is required.'
        if str(error) == 'USERNAME_CONTAINS_SPACE':
            message = f"The username contains white space please remove"
        if str(error) == 'PREFERRED_PHONE_NOT_IN_PHONE_NUMBERS':
            message = 'The preferred phone number must be included in phone_numbers.'
        if str(error) == 'PHONE_NUMBER_ALREADY_OWNED':
            message = 'The phone number is already owned by someone else. Edit on the platform to solve the issue.'
        if str(error) == 'PHONE_NUMBER_TOO_SHORT':
            message = 'The phone number is too short.'
        if str(error) == 'PHONE_NUMBER_TOO_LONG':
            message = 'The phone number is too long.'
        if str(error) == 'PHONE_NUMBER_CONTAINS_SPECIAL_CHARACTERS':
            message = 'The phone number contains special characters.'

        if str(error.args[0]) == 'INVALID_PHONE_NUMBER_EXTENSION':
            message = 'Invalid phone number extension.'
        if str(error.args[0]) == 'INVALID_CASH_AMOUNT':
            message = 'Invalid cash collection amount.'
        if str(error.args[0]) == 'INVALID_EMAIL_FORMAT':
            message = 'Invalid email format.'
        if str(error.args[0]) == 'EMAIL_REQUIRED':
            message = 'The email is required.'
        if str(error) == 'CANNOT_ASSIGN_PERMISSION':
            message = 'Cannot assign permission to the user'
        return message

    @classmethod
    def get_affected_entity(cls, data, user, **kwargs):
        if 'reference_entity_id' in data:
            return OperationalEntitiesGetterService.extract_from_user_and_id(user, data, 'reference_entity_id')
        if 'hub_id' in data:
            return OperationalEntitiesGetterService.get_from_user_and_properties(user, code=str(data.get('hub_id')))
        return None

    @classmethod
    def _send_password_by_email(cls, this_user, raw_password, preferred_password_communication=None, edit=False):
        if not preferred_password_communication:
            preferred_password_communication = config.DEFAULT_PASSWORD_COMMUNICATION
        body = TranslationService.ftext(
            cls.EDITED_PASSWORD_TEMPLATE if edit else cls.NEW_ACCOUNT_EMAIL_TEMPLATE,
            user=this_user,
            recipient=this_user.username,
            raw_password=raw_password,
            payg_url=os.getenv("PAYG_URL", '')
        )
        title = TranslationService.ftext(
            'PaygOps password changed' if edit else 'PaygOps Account created successfully',
            user=this_user
        )
        if preferred_password_communication == 'email':
            if not this_user.email:
                raise Error(f'The user {this_user.full_name} does not have an email to recieve the password')
            EmailSender(
                this_user.full_name,
                this_user.email,
                title,
                body,
                html=True
            ).send()
        elif preferred_password_communication == 'sms':
            number = this_user.person.preferred_phone_number()
            if not number:
                raise Error('The user does not have a phone number to recieve the password')
            SMSSend.SendMessage(number, body)
