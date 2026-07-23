from datetime import datetime
from messages_system.services.message_service import MessageService
from pony.orm import db_session
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.actions.helpers.code_error import handle_device_code_error
from payg_loan_system.contracts.services.contract_termination_service import ContractTerminationService, ContractStatus
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_api_errors import DeviceAPIError
from sales_system.leads.services.add_lead_service import AddLeadService
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from stock_management_system.services.stock_movement_creation_service import StockMovementCreationService


@db_session
def handle_deregistration_request(acting_user, this_device, registration_request_code=None, cancel_contract=False, duplicate_lead=False, send_sms=False, note=None):

    if not StockMovementCreationService.user_can_make_action(this_device.stock_item, acting_user):
        answer = [{'success': False,
                  'status': 'STOCK_ITEM_NOT_VISIBLE',
                  'device_serial': this_device.get_display_name()}]
        return answer

    # We check who owned the device
    this_client = this_device.contract.client if this_device.contract else None
    contract = this_device.contract
    if this_client is None or contract is None:
        return [{'success': False, 'status': 'DEVICE_NOT_REGISTERED'}]
    
    if not cancel_contract and not acting_user.can_access('DeRegisterActions', person=this_client.person):
        answer = [{'success': False,
                  'status': 'INSUFFICIENT_PERMISSION',
                  'permission': 'DeRegisterActions'}]
        return answer

    # We default if not already done
    if contract.status != ContractStatus.defaulted and not cancel_contract:
        default_status = ContractTerminationService.default_contract(contract, acting_user, note)
        if not default_status['success']:
            return [default_status]

    # We cancel
    if contract.status != ContractStatus.defaulted and cancel_contract:
        default_status = ContractTerminationService.cancel_contract(contract, acting_user, note)
        if not default_status['success']:
            return [default_status]

    # We repossess
    device = contract.linked_device
    repossess_status = ContractTerminationService.repossess_device(contract, acting_user, cancel_contract, note)
    if not repossess_status['success']:
        return [repossess_status]
    
    # We count the number of active contracts owned by the client
    active_contracts = this_client.active_contracts.count()

    answer = []

    try:
        DeviceAPIService.sync_device_settings(this_device, registration_request_code)
    except DeviceAPIError as CE:
        # In the case of  de-registration we can let de-register without the device
        answer.append(handle_device_code_error(CE))
        answer.append({'success': True, 'status': 'DEVICE_SYNC_ISSUE_DEREGISTRATION'})

    if active_contracts == 0 and not cancel_contract and not duplicate_lead:
        answer.append({'success': True, 'status': 'CLIENT_DEREGISTRATION_SUCCESS',
                       'client_id': this_client.id, 'name': this_client.person.name,
                       'surname': this_client.person.surname})
        
    elif active_contracts > 0 and not cancel_contract and not duplicate_lead:
        answer.append({'success': True, 'status': 'DEVICE_DEREGISTRATION_SUCCESS', 'device_count': active_contracts,
                       'client_id': this_client.id, 'name': this_client.person.name,
                       'surname': this_client.person.surname, 'device_serial': this_device.get_display_name()})
    elif duplicate_lead:
        LeadStatusChangeService.cancel_lead(contract.lead, acting_user)
        new_lead = AddLeadService.add_lead({
            'contract_reference': contract.reference,
            'allocated_device': device.composed_serial
        }, acting_user)
        view_lead_url = f'/leads/{new_lead.id}'
        markdown_link = f'[Lead]({view_lead_url})'
        answer.append({'success': True, 'status': 'CONTRACT_AND_LEAD_CANCELLATION_SUCCESS', 'contract_reference': contract.reference, 'new_lead': markdown_link})

    else:
        LeadStatusChangeService.cancel_lead(contract.lead, acting_user)
        answer.append({'success': True, 'status': 'CONTRACT_CANCELLATION_SUCCESS', 'contract_reference': contract.reference})
    if send_sms:
        answer_sms = [{'success': True,
                'status': 'CONTRACT_CANCELLED',
                'contract_reference': contract.reference,
                'name': this_client.person.name,
                'surname': this_client.person.surname,
                'device_serial': this_device.get_display_name(),
                'offer_name': contract.offer.name,
                }]

        MessageService.send_answer_to_person(answer_sms, this_client.person)

    save_mentor_request(acting_user, this_client, this_device, registration_request_code)

    return answer


def save_mentor_request(acting_user, this_client, this_device, registration_request_code):
    if registration_request_code is None:
        registration_request_code = str(this_device.composed_serial)
    MentorRequest(ReceptionTime=datetime.now(), Type='DeRegistration', RequestCode=registration_request_code,
                  ActivationTimeAddedInDays=0, Device=this_device,
                  client=this_client, user=acting_user)
