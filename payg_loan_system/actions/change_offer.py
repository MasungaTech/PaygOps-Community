from datetime import datetime
from pony.orm import db_session
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIError
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.offers.models import OfferType
from payg_loan_system.contracts.services.contract_change_service import ContractChangeService
from shared.api_helpers.hook_helpers import process_hook
from core_system.core_entities import db


def handle_offer_change_request(acting_user, registration_request_code=None, new_offer_code=None, note=None,
                                this_contract=None, this_device=None):

    if this_device is None and registration_request_code:
        try:
            this_device = DeviceGetterService.get_device_from_registration_code(registration_request_code)
        except DeviceAPIError as CE:
            return [handle_device_code_error(CE)]
        except ConfigurationError as config_error:
            return [{'success': False,
                    'status': 'CONFIGURATION_ERROR',
                    'error_type': str(config_error)}]

    contract = this_contract or (this_device.contract if this_device else None)
    if this_device is None and contract:
        this_device = contract.linked_device

    this_client = contract.client if contract else None
    if this_client is None:
        return [{'success': False,
                'status': 'DEVICE_NOT_REGISTERED'}]

    if not acting_user.can_access('DoChangeOfferActions', person=this_client.person):
        return [{'success': False,
                'status': 'INSUFFICIENT_PERMISSION',
                'permission': 'DoChangeOfferActions'}]

    new_offer = ListOfferService.get_from_user_and_properties(acting_user, code=new_offer_code)
    if not new_offer:
        return [{'success': False, 'status': 'OFFER_DOES_NOT_EXIST'}]
    if new_offer.type == OfferType.lump_sum:
        return [{'success': False,
                'status': 'NEW_OFFER_LUMP_SUM'}]

    old_offer = contract.offer
    if new_offer.type != old_offer.type:
        return [{'success': False,
                'status': 'NEW_OFFER_TYPE_DIFFERENT'}]
    if this_device and not this_device.can_use_offer(old_offer):
        return [{'success': False,
                 'status': 'DEVICE_NOT_ALLOWED_ON_OFFER'}]
    offer_change_status = ContractChangeService.change_contract_offer(contract, new_offer, acting_user, note)
    if not offer_change_status['success']:
        return [offer_change_status]
    repayments = offer_change_status.pop('repayments')
    registration_answer_code = None
    if this_device:
        try:
            registration_answer_code = DeviceAPIService.sync_device_settings(
                this_device,
                registration_request_code or this_device.composed_serial,
                repayments
            )
        except DeviceAPIError as CE:
            return [handle_device_code_error(CE)]
        except ConfigurationError as config_error:
            return [{'success': False,
                    'status': 'CONFIGURATION_ERROR',
                    'error_type': str(config_error)}]

    if this_device and DeviceAPIService.device_requires_answer_code(this_device):
        status = 'OFFER_CHANGE_SUCCESS'
    elif this_device:
        status = 'OFFER_CHANGE_SUCCESS_NO_CODE'
    else:
        status = 'OFFER_CHANGE_SUCCESS_NO_DEVICE'
    if not new_offer.can_be_completed:
        status += '_NO_PROGRESSION'

    progression = contract.get_weeks_progression_dict()
    main_answer = {
        'success': True,
        'status': status,
        'client_id': this_client.id,
        'name': this_client.person.name,
        'surname': this_client.person.surname,
        'contract_reference': contract.reference,
        'device_serial': this_device.get_display_name() if this_device else None,
        'old_offer_code': old_offer.code,
        'new_offer_code': new_offer_code,
        'weeks_paid': progression['weeks_paid'] if progression else '',
        'days_paid': progression['days_paid'] if progression else '',
        'weeks_to_pay': progression['weeks_to_pay'] if progression else '',
        'days_to_pay': progression['days_to_pay'] if progression else '',
        'remaining_weeks_to_pay': progression['remaining_weeks_to_pay'] if progression else '',
        'remaining_days_to_pay': progression['remaining_days_to_pay'] if progression else '',
        'registration_answer_code': registration_answer_code,
        'acting_user_id': acting_user.id,
        'contract_event_id': offer_change_status.get('contract_event_id')
    }
    answer = [main_answer]

    store_request(registration_request_code or (this_device.composed_serial if this_device else ''),
                  this_device,
                  this_client,
                  acting_user,
                  old_offer,
                  new_offer)

    hook_data = main_answer.copy()
    hook_data.pop('success')
    process_hook.add_hook_after_commit(db, 'offer_changed', hook_data)

    return answer


@db_session
def store_request(reg_code, device, client, user, old_offer, new_offer):
    return MentorRequest(ReceptionTime=datetime.now(),
                         Type='Offer Change',
                         RequestCode=reg_code,
                         Device=device,
                         client=client.id,
                         user=user,
                         AdditionalData='Old Offer:' +
                                        str(old_offer) +
                                        ',New Offer:' +
                                        str(new_offer)
                         )
