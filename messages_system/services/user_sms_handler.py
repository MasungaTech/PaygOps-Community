from core_system.client.services.client_getter_service import ClientGetterService
from messages_system.services.send_sms import SMSSend
from sales_system.leads.lead_sms_app import LeadCreatorSMS
from core_system.client.models import Client
from payg_loan_system.actions.unlock import handle_unlock_request
from payg_loan_system.actions.add_account import handle_add_account_request
from payg_loan_system.actions.activation import handle_activation_request
from payg_loan_system.actions.add_phone_number import handle_add_phone_number_request
from payg_loan_system.actions.direct_activate import handle_direct_activation_request
from payg_loan_system.actions.change_offer import handle_offer_change_request
from payg_loan_system.actions.device_sync_settings import handle_device_sync_settings_request
from payg_loan_system.actions.switch_device_mode import handle_switch_device_mode
from messages_system.services.message_service import MessageService
from payg_loan_system.actions.helpers.code_error import ConfigurationError
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIError
from messages_system.user_command_handlers.register_handler import RegisterSMSCommandService
from messages_system.user_command_handlers.collect_cash_handler import CollectCashSMSCommandService
from messages_system.user_command_handlers.swap_device_handler import SwapDeviceSMSCommandService
from messages_system.user_command_handlers.give_delay_handler import GiveDelaySMSCommandService
from messages_system.user_command_handlers.deregister_handler import DeRegisterSMSCommandService
from messages_system.user_command_handlers.give_discount_handler import GiveDiscountSMSCommandService
from shared.logger.loggers import Error, LogAPI
from shared.api_helpers.hook_helpers.process_hook import process_hook


Log = LogAPI()
sms_answer = SMSSend

def handle_user_SMS(this_user, from_number, body, reception_time):
    """
    Shuttles the SMS command to the proper function on which it will take an action
    :param this_user: User
    :param from_number: Phone number
    :param body: The SMS text body
    :param reception_time:
    :return:
    """
    Log.Event('User message received.')

    if this_user.is_expired():
        sms_answer.SendMessage(from_number, 'You do not have the proper permissions to send requests.', this_user.person)
        return 1

    body_split = body.split('#')

    if len(body_split) != 2:
        status = {'success': False,
                  'status': 'UNKNOWN_USER_REQUEST'}
        human_status = MessageService.get_message(status, person=this_user.person)
        sms_answer.SendMessage(from_number, human_status, this_user.person)
        Log.Error('Invalid command received. The message was "' + str(body) + '"')
        return 1

    command = body_split[0].upper().replace('\n', '').replace('\r', '')
    variables = body_split[1]

    if command == 'REGISTER':
        status = RegisterSMSCommandService.process(this_user,
                                                   from_number,
                                                   variables,
                                                   reception_time)
        human_status = MessageService.get_message(status, person=this_user.person)
        sms_answer.SendMessage(from_number, human_status, this_user.person)
        return human_status

    if command == 'DEREGISTER':
        status = DeRegisterSMSCommandService.process(this_user,
                                                     from_number,
                                                     variables,
                                                     reception_time)
        human_status = MessageService.get_message(status, person=this_user.person)
        sms_answer.SendMessage(from_number, human_status, this_user.person)
        return 1

    if command in ['CHANGEDEVICE', 'SWAPDEVICE']:
        status = SwapDeviceSMSCommandService.process(this_user,
                                                     from_number,
                                                     variables,
                                                     reception_time)
        human_status = MessageService.get_message(status, person=this_user.person)
        sms_answer.SendMessage(from_number, human_status, this_user.person)
        return 1

    if command == 'UNLOCK':
        return unlock_command_handler(this_user, from_number, variables, reception_time)

    if command in ['GETCODE', 'SYNCACTIVATION']:
        return getcode_command_handler(this_user, from_number, variables, reception_time)

    if command in ['PAYCASH', 'COLLECTCASH']:
        status = CollectCashSMSCommandService.process(this_user,
                                                      from_number,
                                                      variables,
                                                      reception_time)
        human_status = MessageService.get_message(status, person=this_user.person)
        sms_answer.SendMessage(from_number, human_status, this_user.person)
        return 1

    if command in ['ADDMPESA', 'ADDMOBILEMONEY']:
        return addmpesa_command_handler(this_user, from_number, variables, reception_time)

    if command == 'ADDPHONENUMBER':
        return addphonenumber_command_handler(this_user, from_number, variables, reception_time)

    if command in ['ADDFREETIME', 'GIVEDISCOUNT']:
        status = GiveDiscountSMSCommandService.process(this_user,
                                                       from_number,
                                                       variables,
                                                       reception_time)
        human_status = MessageService.get_message(status, person=this_user.person)
        sms_answer.SendMessage(from_number, human_status, this_user.person)
        return 1

    if command in ['ADDTIME', 'GIVEDELAY']:
        status = GiveDelaySMSCommandService.process(this_user,
                                                    from_number,
                                                    variables,
                                                    reception_time)
        human_status = MessageService.get_message(status, person=this_user.person)
        sms_answer.SendMessage(from_number, human_status, this_user.person)
        return 1

    if command == 'FORCEACTIVATE':
        return forceactivate_command_handler(this_user, from_number, variables, reception_time)

    if command == 'CHANGEOFFER':
        return changeoffer_command_handler(this_user, from_number, variables, reception_time)

    if command == 'SYNCSETTINGS':
        return syncsettings_command_handler(this_user, from_number, variables, reception_time)

    if command == 'DEBIT':
        #return debit_command_handler(this_user, from_number, variables, reception_time)
        # Command disabled
        return process_unknown_request(this_user,
                                       from_number,
                                       command,
                                       variables,
                                       reception_time,
                                       body)

    if command == 'CREATELEAD':
        return enter_lead_command_handler(this_user,
                                          from_number,
                                          variables,
                                          reception_time)

    if command == 'ENABLEPAYG':
        return switch_device_payg_mode_command_handler(this_user,
                                                       from_number,
                                                       variables,
                                                       reception_time,
                                                       True)

    if command == 'DISABLEPAYG':
        return switch_device_payg_mode_command_handler(this_user,
                                                       from_number,
                                                       variables,
                                                       reception_time,
                                                       False)

    return process_unknown_request(this_user,
                                   from_number,
                                   command,
                                   variables,
                                   reception_time,
                                   body)


# -------

def process_unknown_request(this_user, from_number, command, variables, reception_time, body):
    status = {
        'success': False,
        'status': 'UNKNOWN_USER_REQUEST'
    }
    Log.Error('Invalid command received. The message was "' + str(body) + '"')

    human_status = MessageService.get_message(status, person=this_user.person)
    sms_answer.SendMessage(from_number, human_status, this_user.person)

    variables_array = variables.split('*')
    process_hook('unknown_user_sms_command', {
        'command': command,
        'variables': variables_array,
        'user_id': this_user.id,
        'user_name': this_user.person.name,
        'user_surname': this_user.person.surname,
        'from_number': from_number,
    })

    return 1


def switch_device_payg_mode_command_handler(this_user, from_number, variables, reception_time, enable):
    BodyCore = variables.split('*')
    if len(BodyCore) == 1:
        registration_request_code = BodyCore[0]

        if enable:
            Status = handle_switch_device_mode(this_user, 1, registration_request_code)
        else:
            Status = handle_switch_device_mode(this_user, 3, registration_request_code)

        HumanStatus = MessageService.get_message(Status, person=this_user.person)
        sms_answer.SendMessage(from_number, HumanStatus, this_user.person)
        return 1

    else:
        MessageService.send_wrong_request(from_number, this_user.person)
        if enable:
            sms_answer.SendMessage(from_number, 'The request should be ENABLEPAYG# REGISTRATION_CODE', this_user.person)
        else:
            sms_answer.SendMessage(from_number, 'The request should be DISABLEPAYG# REGISTRATION_CODE', this_user.person)
        return 1


def enter_lead_command_handler(user, from_number, variables, reception_time):
    status = LeadCreatorSMS.create(user, from_number, variables, reception_time)
    HumanStatus = MessageService.get_message(status, person=user.person)
    sms_answer.SendMessage(from_number, HumanStatus, user.person)
    return 1


def syncsettings_command_handler(this_user, from_number, variables, reception_time):
    BodyCore = variables.split('*')
    if len(BodyCore) == 1:
        registration_request_code = BodyCore[0]

        Status = handle_device_sync_settings_request(this_user, registration_request_code)
        HumanStatus = MessageService.get_message(Status, person=this_user.person, for_client=False)
        sms_answer.SendMessage(from_number, HumanStatus, this_user.person)
        return 1

    else:
        MessageService.send_wrong_request(from_number, this_user.person)
        sms_answer.SendMessage(from_number, 'The request should be SYNCSETTINGS# REGISTRATION_CODE', this_user.person)
        return 1


def changeoffer_command_handler(this_user, from_number, variables, reception_time):
    BodyCore = variables.split('*')
    if len(BodyCore) == 2:
        registration_request_code = BodyCore[0]
        new_offer_code = BodyCore[1]

        Status = handle_offer_change_request(this_user, registration_request_code, new_offer_code)
        HumanStatus = MessageService.get_message(Status, person=this_user.person)
        sms_answer.SendMessage(from_number, HumanStatus, this_user.person)
        return 1

    else:
        MessageService.send_wrong_request(from_number, this_user.person)
        sms_answer.SendMessage(from_number, 'The request should be CHANGEOFFER# REGISTRATION_CODE * NEW_OFFER_CODE', this_user.person)
        return 1


def forceactivate_command_handler(this_user, from_number, variables, reception_time):
    BodyCore = variables.split('*')

    if len(BodyCore) == 3: # For two-way codes
        activation_request_code = BodyCore[0]
        try:
            this_device_serial = BodyCore[1]
            time_in_days = int(BodyCore[2])
        except:
            MessageService.send_wrong_request(from_number, this_user.person)
            sms_answer.SendMessage(from_number, 'The request should be FORCEACTIVATE# ACTIVATION_CODE * DEVICE_SERIAL * TIME_IN_DAYS', this_user.person)
            return 1

        Status = handle_direct_activation_request(this_user, this_device_serial, activation_request_code, time_in_days)
        HumanStatus = MessageService.get_message(Status, person=this_user.person)
        sms_answer.SendMessage(from_number, HumanStatus, this_user.person)
        return 1

    elif len(BodyCore) == 2: # For one-way code or GSM
        try:
            this_device_serial = BodyCore[0]
            time_in_days = int(BodyCore[1])
        except:
            MessageService.send_wrong_request(from_number, this_user.person)
            sms_answer.SendMessage(from_number, 'The request should be FORCEACTIVATE# DEVICE_SERIAL * TIME_IN_DAYS', this_user.person)
            return 1

        Status = handle_direct_activation_request(this_user, this_device_serial, None, time_in_days)
        HumanStatus = MessageService.get_message(Status, person=this_user.person)
        sms_answer.SendMessage(from_number, HumanStatus, this_user.person)
        return 1

    else:
        MessageService.send_wrong_request(from_number, this_user.person)
        sms_answer.SendMessage(from_number, 'The request should be FORCEACTIVATE# ACTIVATION_CODE * DEVICE_SERIAL * TIME_IN_DAYS', this_user.person)
        return 1


def addmpesa_command_handler(this_user, from_number, variables, reception_time):
    BodyCore = variables.split('*')
    if len(BodyCore) == 2:
        registration_request_code = BodyCore[0]
        transaction_reference = BodyCore[1]

        # TODO: Make function to get device from registration code, returns 1 if good, or a message if bad

        Status = handle_add_account_request(this_user, registration_request_code, transaction_reference)
        HumanStatus = MessageService.get_message(Status, person=this_user.person)
        sms_answer.SendMessage(from_number, HumanStatus)
        return 1

    else:
        MessageService.send_wrong_request(from_number, this_user.person)
        sms_answer.SendMessage(from_number, 'The request should be ADDMOBILEMONEY# REGISTRATIONCODE * PAYMENTREFERENCE', this_user.person)
        return 1


def addphonenumber_command_handler(this_user, from_number, variables, reception_time):
    BodyCore = variables.split('*')
    if len(BodyCore) == 2:
        registration_request_code = BodyCore[0]
        phone_number = BodyCore[1]

        # TODO: Make function to get client from registration code, returns 1 if good, or a message if bad

        Status = handle_add_phone_number_request(this_user, registration_request_code, phone_number)
        HumanStatus = MessageService.get_message(Status, person=this_user.person)
        sms_answer.SendMessage(from_number, HumanStatus, this_user.person)
        return 1

    else:
        MessageService.send_wrong_request(from_number, this_user.person)
        sms_answer.SendMessage(from_number, 'The request should be ADDMPESA# REGISTRATIONCODE * PAYMENTREFERENCE', this_user.person)
        return 1


def unlock_command_handler(this_user, from_number, variables, reception_time):
    BodyCore = variables.split('*')
    if len(BodyCore) == 2:
        unlock_request_code = BodyCore[0]
        try:
            client_id = int(BodyCore[1])
        except:
            sms_answer.SendMessage(from_number, 'The client id should be just a digit, without special symbols. ', this_user.person)
            return 1

        this_client = ClientGetterService.get_from_user_and_id(this_user, client_id)
        if not this_client:
            sms_answer.SendMessage(from_number, "Unknown client id. ", this_user.person)
            return 1

        Status = handle_unlock_request(this_user, this_client, unlock_request_code)
        HumanStatus = MessageService.get_message(Status, person=this_user.person)
        sms_answer.SendMessage(from_number, HumanStatus, this_user.person)
        return 1

    else:
        MessageService.send_wrong_request(from_number, this_user.person)
        sms_answer.SendMessage(from_number, 'Do not forget to include the client id. Ex: UNLOCK#7005631B*123', this_user.person)
        return 1


def getcode_command_handler(this_user, from_number, variables, reception_time):
    BodyCore = variables.split('*')

    # For backward compatibility
    if len(BodyCore) == 1:
        activation_request_code = BodyCore[0]

        # We get the device from the registration code
        try:
            this_device = DeviceGetterService.get_device_from_registration_code(activation_request_code)
        except Error as error:
            sms_answer.SendMessage(from_number, error.get_message(), this_user.person)
            return 1
        except DeviceAPIError as CE:
            sms_answer.SendMessage(from_number, 'Do not forget to include the client id. Ex: GETCODE#7005631B*123', this_user.person)
            return 1
        except ConfigurationError as config_error:
            sms_answer.SendMessage(from_number, 'Do not forget to include the client id. Ex: GETCODE#7005631B*123', this_user.person)
            return 1

        # -----------

        this_client = this_device.contract.client if this_device.contract else None
        if this_client == None:
            sms_answer.SendMessage(from_number, 'Do not forget to include the client id. Ex: GETCODE#7005631B*123', this_user.person)
            return 1

        Status = handle_activation_request(this_client, activation_request_code)
        HumanStatus = MessageService.get_message(Status, person=this_user.person)
        sms_answer.SendMessage(from_number, HumanStatus, this_user.person)
        return 1

    elif len(BodyCore) == 2:
        activation_request_code = BodyCore[0]

        try:
            client_id = int(BodyCore[1])
        except:
            sms_answer.SendMessage(from_number, 'The client id should be just a digit, without special symbols. ', this_user.person)
            return 1

        this_client = ClientGetterService.get_from_user_and_id(this_user, client_id)
        if not this_client:
            sms_answer.SendMessage(from_number, "Unknown client id. ", this_user.person)
            return 1

        Status = handle_activation_request(this_client, activation_request_code)
        HumanStatus = MessageService.get_message(Status, person=this_user.person)
        sms_answer.SendMessage(from_number, HumanStatus, this_user.person)
        return 1

    else:
        MessageService.send_wrong_request(from_number, this_user.person)
        sms_answer.SendMessage(from_number, 'Do not forget to include the client id. Ex: GETCODE#7005631B*123', this_user.person)
        return 1
