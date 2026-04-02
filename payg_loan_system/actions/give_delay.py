from datetime import datetime, timedelta
from pony import orm
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from .activation import sync_activation
from shared.logger.loggers import Error
from shared.api_helpers.hook_helpers import process_hook
from shared.helpers.date_helper import days_until_date
from core_system.core_entities import db


def handle_give_delay_request(acting_user, this_client=None, delayed_days=None, this_device=None, this_contract=None, registration_request_code=None, note=None, delayed_date=None):

    answer = []

    contract = this_contract or (this_device.contract if this_device else None)
    
    if not contract:
        return [{'success': False,
                'status': 'DEVICE_NOT_REGISTERED'}]
    
    if not this_client:
        this_client = contract.client
    
    if not acting_user.can_access('GiveDelayActions', person=contract.client.person):
        return [{'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'GiveDelayActions'}]

    if delayed_date:
        delayed_days = days_until_date(datetime.strptime(delayed_date, "%Y-%m-%d"), contract.next_repayment_due_time)
        
    # Protection against excessive AddFreeTime
    if not acting_user.can_access('GiveDelayOver2DaysActions', person=contract.client.person):
        if delayed_days > 2:
            return [{'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'GiveDelayOver2DaysActions'}]
        else:
            yesterday = datetime.now() - timedelta(days=1)
            addedTimeToday = orm.exists(M for M in MentorRequest if M.client == this_client
                                    and M.Type == 'Add Time' and M.ReceptionTime >= yesterday)
            if addedTimeToday:
                return [{'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'GiveDelayOver2DaysActions'}]

    try:
        repayment = ContractRepaymentService.give_days_grace_period(contract, delayed_days, approver=acting_user, note=note)
    except Error as error:
        if str(error) in ['CONTRACT_COMPLETED', 'CONTRACT_DEFAULTED', 'CONTRACT_PAUSED']:
            return [{'success': False,
                    'status': str(error)}]
        elif 'CREDIT_UNIT_NOT_ALLOWED_FOR_DEVICE' in str(error):
            return [{'success': False,
                    'status': 'CREDIT_UNIT_NOT_ALLOWED_FOR_DEVICE',
                    'allowed_units': error.args[1]}]
        else:
            raise error
    else:
        orm.flush()
        
        main_answer = {
            'success': True,
            'status': 'GIVE_DELAY_SUCCESS',
            'contract_reference': contract.reference,
            'device_serial_number': this_device.composed_serial if this_device else None,
            'client_id': this_client.id,
            'name': this_client.person.name,
            'surname': this_client.person.surname,
            'delayed_days': delayed_days,
            'acting_user_id': acting_user.id,
            'contract_event_id': repayment.contract_event.id if repayment and repayment.contract_event else None
        }
        answer = [main_answer]
        # We prepare and send the hook
        hook_data = main_answer.copy()
        hook_data.pop('success')
        process_hook.add_hook_after_commit(db, 'delay_given', hook_data)

    if this_device:
        save_mentor_request(acting_user, this_client, this_device, delayed_days, registration_request_code)

    if this_device and DeviceAPIService.device_can_auto_activate(this_device):
        activation_answer = [sync_activation(contract=contract, allow_negative=True, repayments=[repayment])]
        answer += activation_answer

    return answer


def save_mentor_request(acting_user, this_client, this_device, delayed_days, registration_request_code):
    # We store the action
    if not registration_request_code and this_device:
        registration_request_code = str(this_device.composed_serial)
    MentorRequest(ReceptionTime=datetime.now(), Type='Add Time', RequestCode=registration_request_code or '',
                  ActivationTimeAddedInDays=int(delayed_days), Device=this_device,
                  client=this_client, user=acting_user)
