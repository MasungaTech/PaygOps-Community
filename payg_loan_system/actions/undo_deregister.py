from datetime import datetime
from pony.orm import db_session, rollback
from payg_loan_system.actions.helpers.code_error import handle_device_code_error
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_getter_service import DeviceAPIError
from payg_loan_system.contracts.services.contract_undo_termination_service import (
    ContractUndoTerminationService)
from shared.api_helpers.hook_helpers.process_hook import process_hook
from .activation import sync_activation
from shared.logger.loggers import LogAPI, Error

logger = LogAPI()


def undo_deregister(acting_user, this_contract, this_device=None, registration_request_code=None, note=None):

    if not acting_user.can_access('UndoContractDefaultedActions', person=this_contract.client.person):
        answer = [{'success': False,
                  'status': 'INSUFFICIENT_PERMISSION',
                  'permission': 'RegisterActions'}]
        return answer

    try:
        contract_response = ContractUndoTerminationService.undo_default(this_contract, acting_user, this_device, note)
        if not contract_response['success']:
            return [contract_response]
    except Exception as error:
        logger.Fatal(error)
        return [{'success': False,
                'status': 'UNKNOWN_ERROR',
                'error_message': str(error)}]

    this_device = this_contract.linked_device

    try:
        registration_answer_code = DeviceAPIService.sync_device_settings(this_device,
                                                                         registration_request_code)
    except DeviceAPIError as CE:
        return [handle_device_code_error(CE)]  # We call the generic code error handler here to give a readable output
    except Exception as other_error:
        logger.Fatal(other_error)
        return [{'success': False,
                'status': 'UNKNOWN_ERROR',
                'error_message': str(other_error)}]

    if DeviceAPIService.device_requires_answer_code(this_device):
        status = 'UNDO_DEFAULT_SUCCESS'
    else:
        status = 'UNDO_DEFAULT_SUCCESS_NO_CODE'

    client = this_contract.client

    answer = [{'success': True,
               'status': status,
               'registration_answer_code': registration_answer_code,
               'name': client.person.name,
               'surname': client.person.surname,
               'client_id': client.id,
               'device_serial': this_device.get_display_name() if this_device else None,
               'contract_reference': this_contract.reference}]

    # We store a trace of the action
    save_mentor_request(registration_request_code,
                        acting_user,
                        this_device,
                        client)

    # We Auto-Activate if necessary
    if DeviceAPIService.device_can_auto_activate(this_device):
        activation_answer = sync_activation(this_contract)
        answer += [activation_answer]

    return answer


@db_session
def save_mentor_request(reg_code, user, device, client):
    if not reg_code and device:
        reg_code = str(device.composed_serial)
    elif not reg_code and not device:
        reg_code = 'No Device'
    return MentorRequest(ReceptionTime=datetime.now(),
                         Type='Undo Default',
                         RequestCode=reg_code,
                         user=user,
                         ActivationTimeAddedInDays=0,
                         Device=device,
                         client=client.id)
