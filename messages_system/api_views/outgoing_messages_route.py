from datetime import datetime
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.phone_numbers.services.phone_number_finder import PhoneNumberFinder
from core_system.users.services.user_getter_service import UserGetterService
from messages_system.models.sms_db import OutgoingSMS
from messages_system.services.send_sms import SMSSend
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService


MULTIPLE_DESTINATIONS_ERROR = Error('You can only specify one of the following: number, user, client, lead or generator', code="MULTIPLE_DESTINATIONS_ERROR")
PHONE_NOT_FOUND_FOR_PERSON = Error('No phone number was found for that person', code="PHONE_NOT_FOUND_FOR_PERSON")

class OutgoingSMSService(BaseGetterService):

    OBJ_NAME = 'Outgoing SMS'

    @classmethod
    def _add_from_data_and_user(cls, data, current_user):
        number = data.get('to_number')
        user_id = data.get('to_user_id')
        client_id = data.get('to_client_id')
        lead_id = data.get('to_lead_id')
        generator_id = data.get('to_generator_id')
    
        if not number and not user_id and not client_id and not lead_id and not generator_id:
            raise Error('You must specify one of the following: number, user, client, lead or generator', code="DESTINATION_MISSING_ERROR")
        
        if number:
            if user_id or client_id or lead_id or generator_id:
                raise MULTIPLE_DESTINATIONS_ERROR
            person = None
        else:
            if user_id:
                if client_id or lead_id or generator_id:
                    raise MULTIPLE_DESTINATIONS_ERROR
                user = UserGetterService.get_from_user_and_id(current_user, user_id)
                if not user:
                    raise Error('User not found', code="USER_NOT_FOUND_ERROR")
                person = user.person
            if client_id:
                if lead_id or generator_id:
                    raise MULTIPLE_DESTINATIONS_ERROR
                client = ClientGetterService.get_from_user_and_id(current_user, client_id)
                if not client:
                    raise Error('Client not found', code="CLIENT_NOT_FOUND_ERROR")
                person = client.person
            if lead_id:
                if generator_id:
                    raise MULTIPLE_DESTINATIONS_ERROR
                lead = LeadGetterService.get_from_user_and_id(current_user, lead_id)
                if not lead:
                    raise Error('Lead not found', code="LEAD_NOT_FOUND_ERROR")
                person = lead.person
            if generator_id:
                generator = LeadGeneratorGetterService.get_from_user_and_id(current_user, generator_id)
                if not generator:
                    raise Error('Lead Generator not found', code="GENERATOR_NOT_FOUND_ERROR")
                person = generator.person

            number = PhoneNumberFinder.find_person_preferred_number(person)
            if not number:
                raise PHONE_NOT_FOUND_FOR_PERSON
        return SMSSend.SendMessage(number, data["body"], person, current_user)

    @classmethod
    def preprocess_list_filters(cls, user, **kwargs):
        if kwargs.get('sent'):
            kwargs['sent'] == kwargs['sent'] in ['true', 'True']
        return kwargs

    @classmethod
    def get_filtered_objects(cls, current_user, sent=None, from_date=None, to_date=None, to_number=None, status=None, **kwargs):
        messages = OutgoingSMS.select()
        if sent:
            messages = messages.filter(lambda m: m.IsSent == sent)
        if status:
            messages = messages.filter(lambda m: m.status == status)
        if from_date:
            messages = messages.filter(lambda m: m.SendingTime >= from_date)
        if to_date:
            messages = messages.filter(lambda m: m.SendingTime < to_date)
        if to_number:
            messages = messages.filter(lambda m: to_number in m.ToNumber)
        return messages

class OutgoingMessageResource(BaseAPIResourceAll):

    ADD_SERVICE = OutgoingSMSService
    ADD_PERMISSION = 'AddOutgoingMessages'
    MODEL = OutgoingSMS
    TAG = 'Miscellaneous'
    LIST_SERVICE = OutgoingSMSService
    LIST_PERMISSION = 'ViewMessages'

    EXTRA_LIST_PARAMS = {
        'status': {
            'in': 'query',
            'name': 'status',
            'schema': {
                "type": "string",
                "enum": ['created', 'processed', 'sent', 'sending_failure', 'sending_rejected', 'sending_rejected_config', 'sending_rejected_msisdn', 'sending_rejected_flagged', 'delivered_telco', 'delivered_final', 'delivery_failure', 'delivery_rejected', 'delivery_failure_absent', 'delivery_rejected_msisdn', 'delivery_rejected_flagged']
            },
            'example': 'sending_failure',
            'allowEmptyValue': True,
            'description': 'Allows for filtering sent messsages by status'
        },
        'from_date': {
            'in': 'query',
            'name': 'from_date',
            'schema': {
                'type': 'string',
                'format': 'date-time'
            },
            'example': datetime.now().isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering messages sent after this time'
        },
        'to_date': {
            'in': 'query',
            'name': 'to_date',
            'schema': {
                'type': 'string',
                'format': 'date-time'
            },
            'example': datetime.now().isoformat(),
            'allowEmptyValue': True,
            'description': 'Allows for filtering messages sent before this time'
        },
        'to_number': {
            'in': 'query',
            'name': 'to_number',
            'schema': {
                'type': 'string',
            },
            'example': '+123456789',
            'allowEmptyValue': True,
            'description': 'Allows for filtering messegges sent to an specific number'
        },
        'sent': {
            'in': 'query',
            'name': 'sent',
            'schema': {
                "type": "string",
                "enum": ['true', 'false', 'True', 'False']
            },
            'example': 'all',
            'allowEmptyValue': True,
            'deprecated': True,
            'description': 'Allows for filtering just sent or not sent messages'
        },
    }
