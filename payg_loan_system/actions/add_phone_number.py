from payg_loan_system.requests.models import MentorRequest
from core_system.phone_numbers.model import PhoneNumbers
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.devices.device_api.device_getter_service import *
from datetime import datetime
from core_system.phone_numbers.services.add_phone_number_service import AddPhoneNumberService


def handle_add_phone_number_request(acting_user, registration_request_code, phone_number):

    answer = []

    # We get the device from the registration code
    try:
        this_device = DeviceGetterService.get_device_from_registration_code(registration_request_code)
    except DeviceAPIError as CE:
        return [handle_device_code_error(CE)]  # We call the generic code error handler here to give a readable output
    except ConfigurationError as config_error:
        return {'success': False, 'status': 'CONFIGURATION_ERROR', 'error_type': str(config_error)}

    this_client = this_device.contract.client if this_device.contract else None
    if this_device.contract is None:
        return {'success': False, 'status': 'DEVICE_NOT_REGISTERED'}


    # ---------------


    # We check if we know the phone number and add it to the device owner if necessary
    PhoneNumberRegistered = PhoneNumbers.get(number=phone_number)
    if PhoneNumberRegistered is None:
        AddPhoneNumberService.add_phone_numbers_to_person([phone_number], this_client.person)
        answer = {'success': True, 'status': 'ADD_PHONE_NUMBER_SUCCESS',
                  'name': this_client.person.name, 'surname': this_client.person.surname,
                  'client_id': this_client.id,
                  'phone_number': phone_number}
    else:
        old_person = PhoneNumberRegistered.person
        if old_person and old_person.client:
            old_client = old_person.client
            AddPhoneNumberService.add_phone_numbers_to_person([phone_number], this_client.person)
            answer = {'success': True, 'status': 'ADD_EXISTING_PHONE_NUMBER_SUCCESS',
                      'name': this_client.person.name, 'surname': this_client.person.surname,
                      'client_id': this_client.id,
                      'old_client_name': old_client.full_name, 'old_client_id': old_client.id,
                      'phone_number': phone_number}
        else:
            answer = {'success': True, 'status': 'ADD_PHONE_NUMBER_SUCCESS',
                      'name': this_client.person.name, 'surname': this_client.person.surname,
                      'client_id': this_client.id,
                      'phone_number': phone_number}


    # We store a trace of the action
    MentorRequest(ReceptionTime=datetime.now(), Type='Add Phone Number', RequestCode=registration_request_code,
                  ActivationTimeAddedInDays=0, CreditsAdded=0, user=acting_user,
                  Device=this_device, client=this_client,
                  AdditionalData='Number:' + phone_number)

    return answer
