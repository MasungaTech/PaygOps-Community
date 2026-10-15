from datetime import datetime
from pony.orm import db_session
from payg_loan_system.contracts.services.contract_termination_service import (
    ContractTerminationService)
from payg_loan_system.requests.models import MentorRequest

@db_session
def handle_default_request(acting_user, this_device=None, this_contract=None, registration_request_code=None, note=None):

    # We check who owned the device
    if this_device:
        this_client = this_device.contract.client if this_device.contract else None
        contract = this_device.contract
    elif this_contract:
        this_client = this_contract.client
        contract = this_contract
    else:
        return [{'success': False, 'status': 'DEVICE_NOT_REGISTERED'}]

    if this_client is None or contract is None:
        return [{'success': False, 'status': 'DEVICE_NOT_REGISTERED'}]
    
    if not acting_user.can_access('MarkContractDefaultedActions', person=this_client.person):
        answer = [{'success': False,
                  'status': 'INSUFFICIENT_PERMISSION',
                  'permission': 'MarkContractDefaultedActions'}]
        return answer

    # We default if not already done
    default_status = ContractTerminationService.default_contract(contract, acting_user, note)
    if not default_status['success']:
        return [default_status]

    save_mentor_request(acting_user, this_client, this_device, registration_request_code)

    return [{
        'success': True,
        'status': 'CONTRACT_DEFAULT_SUCCESS',
        'client_id': this_client.id,
        'name': this_client.person.name,
        'surname': this_client.person.surname,
        'contract_reference': contract.reference
    }]


def save_mentor_request(acting_user, this_client, this_device, registration_request_code):
    if registration_request_code is None and this_device:
        registration_request_code = str(this_device.composed_serial)
    elif registration_request_code is None and not this_device:
        registration_request_code = 'No Device'
    MentorRequest(ReceptionTime=datetime.now(), Type='Default', RequestCode=registration_request_code,
                  ActivationTimeAddedInDays=0, Device=this_device,
                  client=this_client, user=acting_user)
