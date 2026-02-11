from datetime import datetime
from pony.orm import rollback
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService, DeviceAPIError
from payg_loan_system.devices.model.device_mode import DeviceMode
from payg_loan_system.contracts.models.contract_status import ContractStatus


def handle_switch_device_mode(acting_user, new_mode, registration_request_code):

    answer = []

    # We get the two devices
    try:
        this_device = DeviceGetterService.get_device_from_registration_code(registration_request_code)
    except DeviceAPIError as CE:
        return [handle_device_code_error(CE)]  # We call the generic code error handler here to give a readable output
    except ConfigurationError as config_error:
        return {'success': False, 'status': 'CONFIGURATION_ERROR', 'error_type': str(config_error)}

    contract = this_device.contract
    thisClient = contract.client if contract else None

    if (not thisClient and not acting_user.can_access_in_all('ChangePAYGModeDevices')) or (thisClient and not acting_user.can_access('ChangePAYGModeDevices', person=thisClient.person)):
        return {'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'ChangePAYGModeDevices'}

    # if the Device is not clearly in a state where it should be fully activated
    requires_permissions = False
    if new_mode == DeviceMode.disabled:
        if thisClient is None:
            requires_permissions = True
        elif contract.status != ContractStatus.completed:
            requires_permissions = True

    if requires_permissions and not acting_user.can_access('ForcePAYGModeDevices', person=thisClient.person):
        return {'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'ForcePAYGModeDevices'}

    if this_device.Mode == new_mode:
        answer.append({'status': 'DEVICE_ALREADY_IN_MODE'})

    this_device.Mode = new_mode


    try:
        registration_answer_code = DeviceAPIService.sync_device_settings(this_device,
                                                                         registration_request_code)
    except DeviceAPIError as CE:
        return [handle_device_code_error(CE)]  # We call the generic code error handler here to give a readable output
    except ConfigurationError as config_error:
        return {'success': False, 'status': 'CONFIGURATION_ERROR', 'error_type': str(config_error)}

    if new_mode == 1:
        answer.append({'success': True, 'status': 'DEVICE_ENABLE_PAYG',
                  'registration_answer_code': registration_answer_code,
                  'device_serial': this_device.get_display_name()})
        Type = 'Enable PAYG'
    elif new_mode == 3:
        answer.append({'success': True, 'status': 'DEVICE_DISABLE_PAYG',
                  'registration_answer_code': registration_answer_code,
                  'device_serial': this_device.get_display_name()})
        Type = 'Disable PAYG'

    # We store a trace of the action
    MentorRequest(ReceptionTime=datetime.now(), Type=Type, RequestCode=registration_request_code,
                  user=acting_user,
                  ActivationTimeAddedInDays=0, Device=this_device,
                  client=thisClient,
                  AdditionalData='')

    return answer
