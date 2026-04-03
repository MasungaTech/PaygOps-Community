from datetime import datetime
from pony.orm import db_session
from messages_system.services.notifications_service import NotificationsService
from payg_loan_system.actions.helpers.code_error import handle_device_code_error
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_getter_service import DeviceAPIError
from payg_loan_system.contracts.services.contract_creation_service import ContractCreationService
from payg_loan_system.actions.activation import sync_activation
from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
from payg_loan_system.offers.models import OfferType
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from messages_system.services.message_service import MessageService
from shared.services.settings_service import SettingsService
from stock_management_system.services.stock_movement_creation_service import (
    StockMovementCreationService)
from shared.logger.loggers import LogAPI, Error
from core_system.core_entities import db



def register_lead(acting_user, this_lead, this_device, registration_request_code=None, transaction=None, offline=False, contract_mobile_uuid=None, undelivered_addons=None, delivered_addons=None, note=''):

    undelivered_addons = undelivered_addons or []
    delivered_addons = delivered_addons or []

    # If no explicit delivery selection is provided, use the global default.
    # This keeps auto-registration and manual registration behavior aligned.
    if not undelivered_addons and not delivered_addons and SettingsService.get_setting('MarkAddOnsNotDeliveredDefault'):
        undelivered_addons = [addon.id for addon in this_lead.not_contract_term_changes_addons]

    if not acting_user.can_access('RegisterActions', person=this_lead.person):
        if not offline:
            return [{'success': False,
                     'status': 'INSUFFICIENT_PERMISSION',
                     'permission': 'RegisterActions'}]
        LogAPI.Fatal(Error(f'Registering Lead #{this_lead.id} offline without permission by user #{acting_user.id} with device {this_device.composed_serial}'))

    if not SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device' and this_lead.offer and this_lead.offer.linked_to_product:
        if not StockMovementCreationService.user_can_make_action(this_device.stock_item, acting_user):
            if not offline:
                return [{'success': False,
                        'status': 'STOCK_ITEM_NOT_VISIBLE',
                        'device_serial': this_device.get_display_name()}]
            LogAPI.Fatal(Error(f'Registering Lead #{this_lead.id} offline without stock visiblity by user #{acting_user.id} with device {this_device.composed_serial}'))

    if not this_lead.offer_editing_locked:
        if not offline:
            return [{'success': False,
                     'status': 'CANNOT_REGISTER_UNLOCKED_LEAD',
                     'lead_id': this_lead.id}]
        this_lead.offer_editing_locked = True
        ReconciliationService.reconcile_paid_lead_after_editing(this_lead)

    if offline and not this_lead.decision or this_lead.discarded:
        LeadStatusChangeService.approve_lead(this_lead, status_comment='Automatically approved due to offline registration',
                                             user=acting_user, check_permissions=False, send_sms=False)
        LeadStatusChangeService.update(this_lead)
        LogAPI.Fatal(Error(f'Registering Lead #{this_lead.id} offline while not being approved by user #{acting_user.id} with device {this_device.composed_serial}'))

    if offline and this_device.contract is not None and not this_lead.installed:
        NotificationsService.add_device_registered_notification(this_lead, this_device, acting_user)
        raise Error(f'Registering Lead #{this_lead.id} offline by user #{acting_user.id} with device {this_device.composed_serial} which is already registered')

    if delivered_addons:
        for addon in delivered_addons:
            if not addon.device and addon.offer_version.offer.linked_to_product:
                return [{'success': False,
                        'status': 'ADDON_HAS_NO_DEVICE_AND_IS_LINKED_TO_PRODUCT',
                        'addon_reference': addon.reference,
                        'contract_future_reference': this_lead.future_contract_reference
                        }]
                 
    contract_response = ContractCreationService.create_from_lead_and_device(
        this_lead, this_device, acting_user, contract_mobile_uuid, undelivered_addons=undelivered_addons, note=note)
    if not contract_response['success']:
        return [contract_response]
    
    contract = contract_response['contract']

    if contract_response.get('error') == 'REGISTER_ERROR_CLIENT_HAS_ACTIVE_CONTRACT' and not SettingsService.get_setting('AllowMultipleContracts'):
        answer = {
            'success': True,
            'status': 'REGISTER_ERROR_CLIENT_HAS_ACTIVE_CONTRACT',
            'client_id': contract.client.id,
            'lead_id': this_lead.id,
            'device_serial': this_device.get_display_name(),
        }
        return [answer]
    # We should only generate that first token for v1 API devices as v2 API 
    # will auto-generate a concatenated token if needed. 
    # Generating it for v2 devices can cause issue since partners won't send 
    # the first one in the welcome message even if it contains activation days
    registration_answer_code = ''
    if not SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device' and this_lead.offer and this_lead.offer.linked_to_product:
        if not offline and (this_device.get_api_data().get('device_api_version', 'v1') == 'v1' or contract.offer.type == OfferType.lump_sum):
            try:
                registration_answer_code = DeviceAPIService.sync_device_settings(this_device,
                                                                                registration_request_code)
            except DeviceAPIError as CE:
                # We call the generic code error handler here to give a readable output
                return [handle_device_code_error(CE)]
            except Exception as other_error:
                LogAPI.Fatal(other_error)
                return [{'success': False,
                        'status': 'UNKNOWN_ERROR',
                        'error_message': str(other_error)}]


    if registration_answer_code and DeviceAPIService.device_requires_answer_code(this_device):
        status = 'REGISTRATION_FROM_LEAD_SUCCESS'
    else:
        status = 'REGISTRATION_FROM_LEAD_SUCCESS_NO_CODE'

    client = contract.client
    offer = contract.offer
    free_time = offer.free_credit_at_start
    if transaction:
        transaction.client = client

    answer = [{'success': True,
               'status': status,
               'registration_answer_code': registration_answer_code,
               'name': client.person.name,
               'surname': client.person.surname,
               'client_id': client.id,
               'lead_id': this_lead.id,
               'device_serial': this_device.get_display_name() if this_device else None,
               'offer_id': offer.id}]

    # We store a trace of the action
    save_mentor_request(registration_request_code,
                        acting_user,
                        free_time,
                        this_device,
                        client,
                        offer)

    # We Auto-Activate if necessary
    activation_answer = None
    if DeviceAPIService.device_can_auto_activate(this_device) and not offer.type == OfferType.lump_sum:
        if contract.pending_reconciled_payments_filtered:
            activation_answer = ReconciliationService.get_answer_for_contract(contract, force_time=contract.start_time)
        if not (activation_answer and activation_answer[0]['success']):
            activation_answer = [sync_activation(contract, repayments=contract.repayments)]
        answer += activation_answer

    # We send welcome message to client
    activation_answer_code = None
    expiration_time = contract.next_repayment_due_time
    loan_completed = None
    if activation_answer:
        for this_answer in activation_answer:
            if this_answer['status'] in ['ACTIVATION_REQUEST_SUCCESS', 'CREDIT_ACTIVATION_REQUEST_SUCCESS', 'ACTIVATION_TIME_BOUGHT', 'CONTRACT_PAYMENT_MADE', 'CONTRACT_PAYMENT_MADE_MONTHLY', 'CONTRACT_PAYMENT_MADE_USAGE_BASED']:
                if this_answer['success']:
                    activation_answer_code = this_answer['activation_answer_code']
            elif this_answer['status'] == 'LOAN_REPAYMENT_COMPLETED':
                if this_answer['success']:
                    loan_completed = this_answer
    if this_device and offer and offer.linked_to_product and not SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device':
        device_requires_answer_code = DeviceAPIService.device_requires_answer_code(this_device)
    else:
        device_requires_answer_code = False

    if offer.type == OfferType.loan:
        client_status = 'WELCOME_MESSAGE' if activation_answer_code and device_requires_answer_code and not offline else 'WELCOME_MESSAGE_NO_CODE'
    elif offer.type == OfferType.time_based:
        client_status = 'WELCOME_MESSAGE_TIME_BASED' if activation_answer_code and device_requires_answer_code and not offline else 'WELCOME_MESSAGE_TIME_BASED_NO_CODE'
    elif offer.type == OfferType.usage_based:
        client_status = 'WELCOME_MESSAGE_USAGE_BASED' if activation_answer_code and device_requires_answer_code and not offline else 'WELCOME_MESSAGE_USAGE_BASED_NO_CODE'
    elif offer.type == OfferType.lump_sum:
        client_status = 'WELCOME_MESSAGE_LUMP_SUM' if device_requires_answer_code and not offline else 'WELCOME_MESSAGE_LUMP_SUM_NO_CODE'


    # We send a welcome message
    status_client = {
        'success': True,
        'status': client_status,
        'registration_answer_code': registration_answer_code,
        'activation_answer_code': activation_answer_code,
        'expiration_time_day': expiration_time.strftime('%d') if expiration_time else 'N/A',
        'expiration_time_month': expiration_time.strftime('%m') if expiration_time else 'N/A',
        'expiration_time_year': expiration_time.strftime('%Y') if expiration_time else 'N/A',
        'name': client.person.name,
        'surname': client.person.surname,
        'client_id': client.id,
        'device_serial': this_device.get_display_name() if this_device else None,
        'offer_name': offer.name,
        'free_time': free_time,
        'free_credit': free_time,
        'credit_unit': offer.credit_unit,
        'contract_reference': contract.reference
    }
    if contract.offer.type == OfferType.loan:
        status_client.update(ReconciliationService.get_money_progression_data(contract))
    if loan_completed:
        status_client = [status_client, loan_completed]
    MessageService.send_answer_to_person(status_client, client.person)
    return answer


@db_session
def save_mentor_request(reg_code, user, free_time, device, client, offer):
    if device:
        if not reg_code:
            reg_code = str(device.composed_serial)
    else:
        reg_code = offer.code
    return MentorRequest(ReceptionTime=datetime.now(),
                         Type='Registration',
                         RequestCode=reg_code,
                         user=user,
                         ActivationTimeAddedInDays=int(free_time),
                         Device=device if device else None,
                         client=client.id,
                         AdditionalData='Amount Paid:'
                         + str(offer.registration_fee))
