from pony.orm import db_session, flush
from core_system.person.models.person_model import Person
from sales_system.leads.services.lead_getter_service import LeadGetterService
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.services.settings_service import SettingsService
from .model import PhoneNumbers
from flask import url_for
from shared.logger.loggers import Error, LogAPI
from core_system.phone_numbers.services.add_phone_number_service import AddPhoneNumberService
from shared.services.translation_service import TranslationService


@db_session
def save_phone_number(number_id, owner_id):
    phone = PhoneNumbers.get(id=number_id)
    phone.person = Person.get(id=owner_id)
    flash_str = str(phone.number) + " assigned to " + str(phone.person.full_name)
    return phone, flash_str


@db_session
def add_number(number, person, user=None, lead_id=None):
    try:
        res = dict(flash_msg=None, duplicate=False)
        if lead_id:
            lead = LeadGetterService.get_from_user_and_id(user, lead_id)
            lead_in_restricted_state = LeadStatusService.lead_is_in_restricted_status(lead)
            if lead_in_restricted_state and not user.can_access('EditRestrictedPersonalDetailsLeads', person=person):
                raise Error('INSUFFICIENT_PERMISSION', permission='EditRestrictedPersonalDetailsLeads')
    except Error as error:
        res['flash_msg'] = str(error)
        return res
    owner_data = get_owner_data_if_exists(number)
    if owner_data and not SettingsService.get_setting('AllowMultiplePersonsWithSamePhoneNumber'):
        res['flash_msg'] = get_owned_phone_number_message(owner_data)
        res['duplicate'] = True
        return res

    try:
        AddPhoneNumberService.add_phone_numbers_to_person([number], person)
        flush()
    except Error as error:
        res['flash_msg'] = str(error)
        return res
    res['flash_msg'] = TranslationService.ftext("Phone number added", user=user)
    return res


@db_session
def remove_number(number, user, person):
    if not number:
        return
    if number.startswith('++'):
        number = number[1:]
    log_removal_attemp(number)
    phone_number = PhoneNumbers.get(number=number)

    if phone_number and person in phone_number.persons:
        if person.phoneNumbers.count() == 1 and SettingsService.get_setting('LeadInfoSettings')['phone_number']['required'] and not user.can_access('RemoveLastPhoneNumbers', person=person):
            raise Error(f'You cannot remove the last phone number of {person.full_name} as you do not have permission to remove the last number. ', code="LAST_PHONE_REMOVAL_FORBIDDEN")
        if person.contactPhone == phone_number:
            person.contactPhone = None
        phone_number.persons.remove(person)
        if phone_number.person == person:
            phone_number.person = None
        person.before_update()
        log_removal_end(phone_number.number)


@db_session
def set_as_preferred(number, person_id):
    phone_number = PhoneNumbers.get(number=number)
    if phone_number:
        person = phone_number.persons.filter(id=person_id).first()
        if person:
            person.contactPhone = phone_number
            return True
    return False


@db_session
def get_owner_data_if_exists(number):
    phone_number = PhoneNumbers.get(number=number)
    if phone_number:
        owner = phone_number.persons.select().first()
        if owner:
            owner_dict = {
                'full_name': owner.full_name,
                'person_id': owner.id,
                'client_id': owner.client.id if owner.client else None,
                'user_id': owner.user.id if owner.user else None,
                'leads_ids': [l.id for l in owner.lead],
                'lead_generator_id': owner.leadGenerator.id if owner.leadGenerator else None,
                'number': phone_number.number
            }
            return owner_dict
    return None


@db_session
def get_owned_phone_number_message(owner_dict):
    message = '<span>The phone number already exists, it belongs to <var>{full_name}</var>'.format(full_name=owner_dict['full_name'])
    if owner_dict['client_id']:
        message += '. <a href="{url}" target="_blank"> Client {client_id}</a> '.format(url=url_for('client.view_client',
                                                                      client_id=owner_dict['client_id']),
                                                          client_id=owner_dict['client_id'])
        person = Person.select(lambda p: p.client.id == owner_dict['client_id']).get()
    if owner_dict['user_id']:
        message += '. <a href="{url}" target="_blank"> User {user_id}</a> '.format(url=url_for('user.view_user',
                                                                      user_id=owner_dict['user_id']),
                                                          user_id=owner_dict['user_id'])
        person = Person.select(lambda p: p.user.id == owner_dict['user_id']).get()
    if owner_dict['leads_ids']:
        message += '. <a href="{url}" target="_blank"> Lead {lead_id}</a> '.format(url=url_for('leads.view_lead',
                                                                      lead_id=owner_dict['leads_ids'][0]),
                                                          lead_id=owner_dict['leads_ids'][0])
        person = Person.select(lambda p: owner_dict['leads_ids'][0] in p.lead.id).get()
        
    if owner_dict['lead_generator_id']:
        message += '. <a href="{url}" target="_blank"> Lead Generator {lead_generator_id}</a> '.format(
            url=url_for('lead_generator.view_lead_generator', generator_id=owner_dict['lead_generator_id']),
            lead_generator_id=owner_dict['lead_generator_id'])
        person = Person.select(lambda p: p.leadGenerator.id == owner_dict['lead_generator_id']).get()
        
    message += '</span>. | <br><a onclick="removeNumber(\'{number}\', {person_id}, false);" style="cursor: pointer;">' \
               '<strong>REMOVE FROM OWNER</strong></a> '.format(number=owner_dict['number'], person_id=person.id)
    return message

def log_removal_attemp(phonenumber):
    message = f'[{__name__}]: Removing phone number: {phonenumber}'
    LogAPI().Event(message)

def log_removal_end(phonenumber):
    message = f'[{__name__}]: removal of relationship person-phone_number {phonenumber} ended'
    LogAPI().Event(message)

def ensure_heading_plus_sign(data):
    result = data

    if not data.startswith('+'):
        result = '+' + data

    return result
