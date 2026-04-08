import re
from messages_system.models.custom_message import CustomMessage
from messages_system.services.notifications_service import NotificationsService
from core_system.phone_numbers.services.phone_number_finder import PhoneNumberFinder
from messages_system.services.send_sms import SMSSend
from shared.services.settings_service import SettingsService
from shared.logger.loggers import LogAPI
from config import CUSTOMISABLE_MSGS_INFO, SMS_VARIABLES_INFO, CONTROL_CHARS, TRANSLATION_FOLDER, AVAILABLE_CLIENTS_SMS_LANGUAGES
import jinja2
import markdown
import json
from shared.services.base_service import BaseService


logger = LogAPI()


class MessageService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        return cls.set_custom_message(data['key'], data['template'], data['language'], remove_if_default=False)
    
    @classmethod
    def _delete_from_object_and_user(cls, message, user):
        cls.remove_custom_message(message.key, message.language)

    @classmethod
    def set_custom_message(cls, key, template, language, remove_if_default=True):

        if not cls.valid_custom_key(key):
            raise Exception('MESSAGE_KEY_NOT_CUSTOMISABLE')
        
        for pattern, value in CONTROL_CHARS.items():
            template = re.sub(pattern, value, template)
        ex_status = {x: SMS_VARIABLES_INFO[x]['example'] for x in CUSTOMISABLE_MSGS_INFO[key]['variables']}
        ans, suc = cls.format_template_if_valid(template, ex_status)
        if not suc:
            raise KeyError('Invalid variable '+ans+' in custom message template for '+key+' in '+language)
        
        if remove_if_default and template == cls.get_default_template(key, language):
            cls.remove_custom_message(key, language)
        else:
            msg = CustomMessage.select(lambda cm: cm.key == key and cm.language == language)
            if msg:
                msg.first().template = template
                return msg.first()
            else:
                return CustomMessage(key=key, template=template, language=language)
    
    @classmethod
    def remove_custom_message(cls, key, language):
        template = CustomMessage.get(key=key, language=language)
        if template:
            template.delete()

    @classmethod
    def get_message(cls, status, language=None, person=None, default=False, for_client=None, fallback_to_status=False, markdown_format=False):
        if not language:
            language = SettingsService.get_setting('DefaultSMSUsersLanguage')
        if person is not None and language == SettingsService.get_setting('DefaultSMSUsersLanguage'):
            language = person.get_sms_language()
        if for_client is None:
            for_client = bool(person and (person.client or person.lead))
        if isinstance(status, list):
            answer = ''
            for s in status:
                answer += cls.get_message(s, language, default=default, for_client=for_client, fallback_to_status=fallback_to_status, markdown_format=markdown_format) + '\n'
            return answer[:-1]

        try:
            answer_format = cls.get_template(status['status'], language, default=default, for_client=for_client)
            # We do this to always include at least the default message for the user if it is disabled for clients
            if not for_client and not answer_format:
                answer_format = cls.get_template(status['status'], language, default=True, for_client=for_client)
        except KeyError as exception:
            if for_client:
                return ''
            if fallback_to_status:
                try:
                    return status.get('error_message', status['status'])
                except KeyError as e2:
                    exception = e2
            logger.Fatal(exception)
            return 'Unknown message key: '+str(status)
        except Exception as exception:
            logger.Fatal(exception)
            return 'Something went wrong while generating the answer! Status: '+str(status)

        status_extended = status
        status_extended['currency_sym'] = SettingsService.get_setting('CurrencySymbol')
        answer, success = cls.format_template_if_valid(answer_format, status_extended)
        if not success:
            answer, success = cls.format_template_if_valid(
                cls.get_default_template(status['status'], language, for_client=for_client), status_extended)
            if not success:
                raise Exception('Invalid default message template for '+status['status']+' in '+language+'. Details: '+answer)
            logger.Error('Invalid message template for '+status['status']+' in '+language)
        if  markdown_format:
            return re.sub("(^<p>|</p>$)", "", markdown.markdown(answer), flags=re.IGNORECASE)
        return answer

    @staticmethod
    def format_template_if_valid(template, status):
        try:
            template = template.replace("{", "{{").replace("}", "}}")
            template_jinja = jinja2.Template(template, undefined=jinja2.StrictUndefined)
            return template_jinja.render(**status), True
        except Exception as error:
            logger.Fatal(error)
            return error.__str__(), False

    @classmethod
    def get_example(cls, key, language, default=False, for_client=True):
        status = {'status': key}
        variables = {x: SMS_VARIABLES_INFO[x]['example'] for x in SMS_VARIABLES_INFO}
        status.update(variables)
        if default:
            return cls.get_message(status, language, default=True, for_client=for_client)
        return cls.get_message(status, language, for_client=for_client)

    @classmethod
    def get_template(cls, key, language, default=False, for_client=True):
        if cls.valid_custom_key(key) and not default:
            if not for_client:
                msg = cls.get_user_specific_template(key, language)
                if msg:
                    return msg
            msg = CustomMessage.get(key=key, language=language)
            if msg:
                return msg.template
        return cls.get_default_template(key, language, for_client=for_client)

    @classmethod
    def get_user_specific_template(cls, key, language):
        try:
            return cls._get_dict(language, 'user')[key].strip()
        except KeyError:
            try:
                return cls._get_dict('EN', 'user')[key].strip()
            except KeyError:
                return key

    @classmethod
    def get_default_template(cls, key, language, for_client=True):
        destination = 'client' if for_client else None
        try:
            return cls._get_dict(language, destination)[key].strip()
        except KeyError:
            try:
                return cls._get_dict('EN', destination)[key].strip()
            except KeyError:
                return key

    @classmethod
    def is_disabled(cls, key, language):

        if cls.valid_custom_key(key):
            msg = CustomMessage.get(key=key, language=language)
            if msg and not msg.template:
                return True
        return False

    @classmethod
    def send_answer_to_person(cls, answer, person, force_phone=None):
        message = cls.get_message(answer, person=person) # to check for_client
        number_to_use = force_phone or PhoneNumberFinder.find_person_preferred_number(person)
        if person and not number_to_use:
            NotificationsService.add_no_phone_notification(person.client or person.lead.select().first())
        return SMSSend.SendMessage(number_to_use, message, person)

    @classmethod
    def send_wrong_request(cls, to_number, person):
            status = {'success': False,
                      'status': 'UNKNOWN_USER_REQUEST'}
            message = cls.get_message(status, SettingsService.get_setting('DefaultSMSUsersLanguage'), person=person)
            SMSSend.SendMessage(to_number, message, person)

    @staticmethod
    def valid_custom_key(key):
        return key in CUSTOMISABLE_MSGS_INFO

    @staticmethod
    def _get_dict(language, destination=None):
        if language not in AVAILABLE_CLIENTS_SMS_LANGUAGES:
            raise ValueError('Language not supported')
        if language == 'CU':
            language = 'EN'
        client = json.loads(open(TRANSLATION_FOLDER+f'{language}/{language}_client_msg.json').read())
        #if language in ['SW']:
        #    language = 'EN' # This is because we don't have user messages in Swahili yet
        user = json.loads(open(TRANSLATION_FOLDER+f'{language}/{language}_msg.json').read())
        globald = dict(client, **user)
        return user if destination == 'user' else client if destination == 'client' else globald
