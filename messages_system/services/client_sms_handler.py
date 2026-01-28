from messages_system.services.send_sms import SMSSend
from payg_loan_system.actions.activation import handle_activation_request
from messages_system.services.message_service import MessageService
from shared.api_helpers.hook_helpers.process_hook import process_hook
from shared.logger.loggers import LogAPI

Log = LogAPI()
SMS_Answer = SMSSend


def handle_client_SMS(this_client, from_number, body, reception_time):
    Log.Event('Client message received.')

    body_data = body.split('#')

    if '#' in body:
        status = {'success': False,
                  'status': 'UNKNOWN_REQUEST'}
        human_status = MessageService.get_message(status, person=this_client.person)
        SMS_Answer.SendMessage(from_number, human_status, this_client.person)

        command = body_data[0]
        variables_array = body_data[1].split('*')
        process_hook('unknown_client_sms_command', {
            'command': command,
            'variables': variables_array,
            'client_id': this_client.id,
            'client_name': this_client.person.name,
            'client_surname': this_client.person.surname,
            'from_number': from_number,
        })

        return 1

    else:
        activation_request_code = body_data[0]

        status = handle_activation_request(this_client, activation_request_code)
        human_status = MessageService.get_message(status, person=this_client.person)
        SMS_Answer.SendMessage(from_number, human_status, this_client.person)

        return 1
