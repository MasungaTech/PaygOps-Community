from datetime import datetime
from pony.orm import flush
from payg_loan_system.contracts.services.contract_event_service import ContractEventService
from stock_management_system.services.stock_movement_creation_service import StockMovementCreationService
from stock_management_system.stock_status import StockStatus


def handle_device_assignment_request(
    acting_user, contract, new_device, contract_addon
):
    """Handles the assignment of a device to a contract addon"""
    
    # Check permissions
    if not acting_user.can_access('SwapDeviceActions', person=contract.client.person):
        return get_error_data('INSUFFICIENT_PERMISSION', permission='SwapDeviceActions')

    # Check stock movement permissions
    if not StockMovementCreationService.user_can_make_action(new_device.stock_item, acting_user):
        return get_error_data('STOCK_ITEM_NOT_VISIBLE', device_serial=new_device.get_display_name())

    # Offer compatibility check
    offer_version = contract_addon.offer_version
    if offer_version.offer.product_type and new_device.type != offer_version.offer.product_type:
        return get_error_data('DEVICE_TYPE_NOT_COMPATIBLE')
    if (offer_version.offer.product_sub_type and 
        new_device.product_sub_type != offer_version.offer.product_sub_type):
        return get_error_data('DEVICE_MODEL_NOT_COMPATIBLE')

    # Assign the device to the addon
    new_device.addon = contract_addon
    flush()

    # Create event for device assignment
    ContractEventService.create_contract_addon_device_assign_event(
        contract=contract,
        approver=acting_user,
        new_device=new_device,
        addon=contract_addon,
        time=datetime.now()
    )

    # Create stock movement
    StockMovementCreationService.create(
        new_device.stock_item,
        StockStatus.installed,
        user=acting_user,
        destination_client=contract.client,
        note=f"[Automatic] Device assignment to addon {contract_addon.reference}",
        manual=False
    )
    contract_addon.delivered = True
    contract_addon.delivery_date = datetime.now()
    flush()
    status = 'DEVICE_ASSIGN_SUCCESS_ADDON_NO_CODE'
    return [{
        'success': True,
        'status': status,
        'new_device_serial_number': new_device.get_display_name(),
        'contract_addon_reference': contract_addon.reference
    }]


def get_error_data(code, **kwargs):
    """Returns formatted error data"""
    return [{
        'success': False,
        'status': code,
        **kwargs
    }]