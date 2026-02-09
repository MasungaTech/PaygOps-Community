from pony.orm import select, db_session
from messages_system.services.client_sms_handler import handle_client_SMS
from messages_system.services.send_sms import SMSSend
from messages_system.services.user_sms_handler import handle_user_SMS
from shared.services.settings_service import SettingsService
from shared.logger.loggers import LogAPI
from core_system.users.models.user_model import User
from core_system.phone_numbers.model import PhoneNumbers
from messages_system.services.message_service import MessageService

Answer = SMSSend


def route_sms(from_number, body, reception_time, person):

    this_user = person.user
    if this_user is not None:
        try:
            return handle_user_SMS(this_user, from_number, body, reception_time)
        except Exception as error:
            LogAPI().Fatal(error)
            message = MessageService.get_message({
                'success': False,
                'status': 'UNKNOWN_ERROR',
                'error_message': str(error)
            }, SettingsService.get_setting('DefaultSMSUsersLanguage'))
            return Answer.SendMessage(from_number, message, person)

    this_client = person.client
    if this_client is not None:
        return handle_client_SMS(this_client, from_number, body, reception_time)

    else:
        message = MessageService.get_message({'success': False, 'status': 'UNKNOWN_SENDER'},
                                             SettingsService.get_setting('DefaultSMSClientsLanguage'), 
                                             for_client=True)
        return Answer.SendMessage(from_number, message)
