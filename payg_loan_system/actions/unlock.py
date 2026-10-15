from payg_loan_system.requests.models import MentorRequest
from datetime import datetime
from payg_loan_system.actions.helpers.code_error import handle_device_code_error

from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService, DeviceAPIError


def handle_unlock_request(acting_user, this_client, unlock_request_code):
    # We log the request
    try:
        this_device = DeviceGetterService.get_device_from_client_and_activation_code_optional(this_client,
                                                                                              unlock_request_code)
    except DeviceAPIError as CE:
        return [handle_device_code_error(CE)]  # We call the generic code error handler here to give a readable output

    # We unlock the device
    try:
        unlock_answer_code = DeviceAPIService.unlock_device(this_device, unlock_request_code)
    except DeviceAPIError as CE:
        return [handle_device_code_error(CE)]  # We call the generic code error handler here to give a readable output

    MentorRequest(ReceptionTime=datetime.now(), Type='Device Unlock', RequestCode=unlock_request_code,
                  user=acting_user,
                  ActivationTimeAddedInDays=0, Device=this_device,
                  client=this_client)

    return {'success': True, 'status': 'UNLOCK_SUCCESS', 'unlock_code': unlock_answer_code}

