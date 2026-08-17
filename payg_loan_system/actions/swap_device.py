from datetime import datetime

from pony.orm import flush, rollback

from core_system.core_entities import db
from payg_loan_system.actions.activation import sync_activation
from payg_loan_system.actions.helpers.code_error import \
    handle_device_code_error
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.services.contract_event_service import \
    ContractEventService
from payg_loan_system.contracts.services.contract_repayment_service import \
    ContractRepaymentService
from payg_loan_system.devices.device_api.device_api_errors import \
    DeviceAPIError
from payg_loan_system.devices.device_api.device_api_service import \
    DeviceAPIService
from payg_loan_system.offers.models import OfferType
from payg_loan_system.requests.models import MentorRequest
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from stock_management_system.services.stock_movement_creation_service import \
    StockMovementCreationService
from stock_management_system.stock_status import StockStatus


def handle_device_change_request(
        acting_user, contract, new_device, registration_request_code_old=None,
        registration_request_code_new=None, contract_addon=None, note=None
):

    if contract_addon:
        # Device swap for contract_addon only
        old_device = contract_addon.device
    else:
        # Device swap for contract
        old_device = contract.linked_device

    if not acting_user.can_access('SwapDeviceActions', person=contract.client.person):
        return get_error_data('INSUFFICIENT_PERMISSION', permission='SwapDeviceActions')

    if not StockMovementCreationService.user_can_make_action(old_device.stock_item, acting_user):
        return get_error_data('STOCK_ITEM_NOT_VISIBLE', device_serial=old_device.get_display_name())

    if not StockMovementCreationService.user_can_make_action(new_device.stock_item, acting_user):
        return get_error_data('STOCK_ITEM_NOT_VISIBLE', device_serial=new_device.get_display_name())

    # Check if new device is already registered
    if new_device.contract is not None:
        return get_error_data(
            'DEVICE_ALREADY_REGISTERED', device_owner_id=new_device.contract.client.id)
    
    # Check if new device is already tied to an Addon
    if new_device.addon is not None:
        return get_error_data('DEVICE_ALREADY_REGISTERED', device_owner_id=new_device.addon.contract.client.id)
    
    # Offer compatibility check
    old_offer = contract.offer
    if not new_device.can_use_offer(old_offer):
        return get_error_data('DEVICE_NOT_ALLOWED_ON_OFFER')
    if not new_device.is_compatible_with_offer(old_offer):
        return get_error_data(
            'DEVICE_NOT_ALLOWED_ON_OFFER', allowed_units=new_device.get_allowed_units())

    # If we're swapping contract devices, set the contract properties on new device
    if not contract_addon:
        new_device.contract = old_device.contract
        new_device.ActiveUntil = old_device.ActiveUntil
        new_device.RegistrationTime = old_device.RegistrationTime
        new_device.credit_balance = old_device.credit_balance
        old_device.clear()
        flush()
    else:
        # If we're swapping contract addon devices, just swap the devices without updating contract details
        new_device.addon = contract_addon
    
     # Sync device status
    ContractRepaymentService.sync_device_status_from_contract(new_device, contract)

    # Create event for device swap based on contract or addon
    if contract_addon:
        ContractEventService.create_contract_addon_device_swap_event(
            contract, acting_user, old_device=old_device, new_device=new_device, addon=contract_addon, note=note
        )
    else:
        ContractEventService.create_contract_device_swap_event(
            contract, acting_user, old_device=old_device, new_device=new_device, note=note
        )

    answer = []
    # We sync the two devices
    if not contract_addon:
        try:
            registration_answer_code_old = DeviceAPIService.sync_device_settings(
                old_device,
                registration_request_code_old
            )
        except DeviceAPIError as error:
            if str(error) != 'INVALID_REGISTRATION_CODE':
                # In the case of  de-registration we can let de-register without the device
                answer.append(handle_device_code_error(error))
                answer.append({'success': True, 'status': 'DEVICE_SYNC_ISSUE_SWAP'})
            registration_answer_code_old = "NOT_SYNCED"

        # We should only generate that first token (for the new device) for v1 API devices as v2 API
        # will auto-generate a concatenated token if needed.
        # Generating it for v2 devices can cause issue since partners won't send
        # the first one in the welcome message even if it contains activation days
        registration_answer_code_new = ''
        if (new_device.get_api_data().get('device_api_version', 'v1') == 'v1') or (
            contract.offer.type == OfferType.lump_sum):
            try:
                registration_answer_code_new = DeviceAPIService.sync_device_settings(
                    new_device,
                    registration_request_code_new
                )
            except DeviceAPIError as error:
                answer.append(handle_device_code_error(error))
                registration_answer_code_new = 'NOT_SYNCED'

        if registration_answer_code_new and DeviceAPIService.device_requires_answer_code(new_device):
            status = 'DEVICE_CHANGE_SUCCESS'
        else:
            status = 'DEVICE_CHANGE_SUCCESS_NO_CODE'


        save_mentor_request(acting_user, old_device, new_device, registration_request_code_old, contract.client)

        client_to_change = contract.client

        send_data_to_hook(client_to_change, acting_user, old_device, new_device, contract)

        movement_1 = StockMovementCreationService.create(
            old_device.stock_item,
            StockStatus.with_user,
            user=acting_user,
            destination_user=acting_user,
            note="[Automatic] Device Swap",
            manual=False,
            suppress_errors=True
        )
        movement_2 = StockMovementCreationService.create(
            new_device.stock_item,
            StockStatus.installed,
            user=acting_user,
            destination_client=client_to_change,
            note="[Automatic] Device Swap",
            manual=False,
            suppress_errors=True
        )
        if not movement_1:
            return get_error_data('STOCK_MOVEMENT_FAILED', device_serial=old_device.get_display_name())
        if not movement_2:
            rollback()
            return get_error_data('STOCK_MOVEMENT_FAILED', device_serial=new_device.get_display_name())

        answer.append({
            'success': True,
            'status': status,
            'client_id': client_to_change.id,
            'name': client_to_change.person.name,
            'surname': client_to_change.person.surname,
            'new_device_serial_number': new_device.get_display_name(),
            'old_device_serial_number': old_device.get_display_name(),
            'registration_answer_code_new':registration_answer_code_new,
            'registration_answer_code_old':registration_answer_code_old
        })
        if contract.status != ContractStatus.paused:
            if (DeviceAPIService.device_can_auto_activate(new_device) and
                not contract.offer.type == OfferType.lump_sum):
                activation_answer = [sync_activation(contract=contract, allow_negative=True)]
                answer += activation_answer

        return answer
    else:
        status = 'DEVICE_CHANGE_SUCCESS_ADDON_NO_CODE'
        answer.append({
            'success': True,
            'status': status,
            'new_device_serial_number': new_device.get_display_name(),
            'old_device_serial_number': old_device.get_display_name(),
            'contract_addon_reference': contract_addon.reference
        })
        return answer


def save_mentor_request(acting_user, old_device, new_device, registration_request_code_old, client):
    if not registration_request_code_old:
        registration_request_code_old = str(old_device.composed_serial)
    MentorRequest(
        ReceptionTime=datetime.now(), Type='Device Change',
        RequestCode=registration_request_code_old,
        Device=new_device, client=client, user=acting_user,
        AdditionalData='Old Device:' + str(old_device.composed_serial)
    )


def send_data_to_hook(client, acting_user, old_device, new_device, contract):
    formatted_data = {
        'client_id': client.id,
        'client_name': client.person.name,
        'client_surname': client.person.surname,
        'contract_reference': contract.reference,
        'old_device_serial_number': old_device.get_display_name(),
        'new_device_serial_number': new_device.get_display_name(),
        'acting_user_id': acting_user.id
    }
    add_hook_after_commit(db, 'device_swapped', formatted_data)

def get_error_data(code, **kwargs):
    return [{**{
        'success': False,
        'status': code
    }, **kwargs}]
 