from datetime import datetime, timedelta
from decimal import Decimal
from pony import orm
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService, ContractStatus
from payg_loan_system.offers.models import OfferType
from shared.logger.loggers import Error
from .activation import sync_activation
from shared.api_helpers.hook_helpers import process_hook


def give_discount(acting_user, this_device=None, this_contract=None, discounted_units=None, registration_request_code=None, discounted_amount=None, note=None):

    answer = []

    contract = this_contract or (this_device.contract if this_device else None)

    if not contract:
        return [{'success': False,
                 'status': 'DEVICE_NOT_REGISTERED'}]

    this_client = contract.client

    if not acting_user.can_access('GiveDiscountActions', person=this_client.person):
        return [{'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'GiveDiscountActions'}]

    if discounted_amount:
        discounted_amount = Decimal(str(discounted_amount))
        discounted_units = contract.get_units_from_amount(discounted_amount,
                                                      allow_below_minimum=True)
    
    if contract.offer.type == OfferType.lump_sum:
        return [{'success': False, 'status': 'GIVE_DISCOUNT_LUMP_SUM'}]

    if (contract.status == ContractStatus.completed and discounted_units < 0
            and not acting_user.can_access('GiveNegativeDiscountToCompletedActions', person=contract.client.person)):
        return [{'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'GiveNegativeDiscountToCompleted'}]

    # Protection against excessive AddFreeTime
    if contract.offer.type != OfferType.usage_based and not acting_user.can_access('GiveDiscountOver2DaysActions', person=contract.client.person):
        if discounted_units > 2:
            return [{'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'GiveDiscountOver2DaysActions'}]
        yesterday = datetime.now() - timedelta(days=1)
        addedTimeToday = orm.exists(M for M in MentorRequest if M.client == this_client
                                and M.Type == 'Add Free Time' and M.ReceptionTime >= yesterday)
        if addedTimeToday:
            return [{'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'GiveDiscountOver2DaysActions'}]

    try:
        if discounted_amount:
            repayment = ContractRepaymentService.give_amount_discount(contract, discounted_amount, approver=acting_user, note=note)
        else:
            repayment = ContractRepaymentService.give_units_discount(contract, discounted_units, approver=acting_user, note=note)
    except Error as error:
        if str(error) in ['CONTRACT_COMPLETED', 'CONTRACT_DEFAULTED', 'CONTRACT_PAUSED']:
            return [{'success': False,
                    'status': str(error)}]
        if str(error) == 'NEGATIVE_CONTRACT_BALANCE_FORBIDDEN':
            return [{'success': False,
                    'status': 'GIVE_DISCOUNT_NEGATIVE_MORE_THAN_PAID'}]
        if str(error) == 'DISCOUNT_MORE_THAN_LEFT_TO_PAY':
            return [{'success': False,
                    'status': 'DISCOUNT_MORE_THAN_LEFT_TO_PAY'}]
        raise error
    else:
        orm.flush()
        if discounted_amount:
            status = 'GIVE_DISCOUNT_SUCCESS_AMOUNT'
        else:
            status = 'GIVE_DISCOUNT_SUCCESS'
            discounted_amount = repayment.amount
            if contract.offer.type == OfferType.usage_based:
                status += '_USAGE_BASED'
            elif contract.offer.is_monthly:
                status += '_MONTHLY'
        main_answer = {
            'success': True,
            'status': status,
            'contract_reference': contract.reference,
            'device_serial_number': this_device.composed_serial if this_device else None,
            'client_id': this_client.id,
            'name': this_client.person.name,
            'surname': this_client.person.surname,
            'unit_name': contract.offer.credit_unit,
            'discounted_units': discounted_units,
            'discounted_days': discounted_units,
            'discounted_amount': discounted_amount,
            'acting_user_id': acting_user.id,
            'contract_event_id': repayment.contract_event.id if repayment and repayment.contract_event else None
        }
        answer = [main_answer]
        progression = contract.get_weeks_progression_dict()
        if progression:
            answer.append({
                'success': True,
                'status': 'PROGRESSION_USER',
                'weeks_paid': progression['weeks_paid'],
                'days_paid': progression['days_paid'],
                'weeks_to_pay': progression['weeks_to_pay'],
                'days_to_pay': progression['days_to_pay'],
                'remaining_weeks_to_pay': progression['remaining_weeks_to_pay'],
                'remaining_days_to_pay': progression['remaining_days_to_pay']
            })

            # We prepare and send the hook
            hook_data = main_answer.copy()
            hook_data.pop('success')
            process_hook.process_hook('discount_given', hook_data)

    if this_device:
        save_mentor_request(acting_user, this_device, discounted_units, this_client,
                            registration_request_code)

    if this_device and DeviceAPIService.device_can_auto_activate(this_device):
        activation_answer = [sync_activation(contract=contract, allow_negative=True, repayments=[repayment])]
        answer += activation_answer

    return answer


def save_mentor_request(acting_user, this_device, discounted_days, ActivatedClient,
                        registration_request_code):
    # We store the action
    if registration_request_code is None and this_device:
        registration_request_code = str(this_device.composed_serial)
    MentorRequest(ReceptionTime=datetime.now(), Type='Add Free Time', RequestCode=registration_request_code or '',
                  ActivationTimeAddedInDays=int(discounted_days), Device=this_device,
                  client=ActivatedClient, user=acting_user)
