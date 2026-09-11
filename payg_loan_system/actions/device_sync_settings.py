from datetime import datetime
from pony.orm import rollback
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_api_errors import DeviceAPIError
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError


def handle_device_sync_settings_request(acting_user, registration_request_code):

    # TODO: Check permissions

    # We get the device from the registration code
    try:
        this_device = DeviceGetterService.get_device_from_registration_code(registration_request_code)
    except DeviceAPIError as CE:
        return [handle_device_code_error(CE)]  # We call the generic code error handler here to give a readable output
    except ConfigurationError as config_error:
        return {'success': False, 'status': 'CONFIGURATION_ERROR', 'error_type': str(config_error)}

    this_client = this_device.contract.client if this_device.contract else None

    try:
        registration_answer_code = DeviceAPIService.sync_device_settings(this_device, registration_request_code)
    except DeviceAPIError as CE:
        return [handle_device_code_error(CE)]  # We call the generic code error handler here to give a readable output
    except ConfigurationError as config_error:
        return {'success': False, 'status': 'CONFIGURATION_ERROR', 'error_type': str(config_error)}

    answer = {'success': True, 'status': 'DEVICE_SETTINGS_SYNC_SUCCESS',
              'registration_answer_code': registration_answer_code,
              'device_serial': this_device.get_display_name()}

    # We store a trace of the action
    MentorRequest(ReceptionTime=datetime.now(), Type='Sync Settings', RequestCode=registration_request_code,
                  user=acting_user,
                  ActivationTimeAddedInDays=0, Device=this_device,
                  client=this_client,
                  AdditionalData='')

    return answer
