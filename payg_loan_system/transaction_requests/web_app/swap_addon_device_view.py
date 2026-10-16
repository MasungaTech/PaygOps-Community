from flask import url_for
from flask_login import login_required, current_user
from pony.orm import db_session
from shared.helpers.select2 import render
from shared.helpers.authorizer import authorizer
from . import transaction_request
from payg_loan_system.devices.device_list_service import DeviceListService
from payg_loan_system.transaction_requests.nonpayg_device_picker import (
    should_show_auto_generated_nonpayg,
)
from payg_loan_system.contracts.services.addon_list_service import AddonListService
from werkzeug.exceptions import NotFound


@transaction_request.route('/swap_addon_device/content/<string:contract_addon_reference>', methods=['GET'])
@login_required
@authorizer('SwapDeviceActions')
@db_session
def swap_addon_device_transaction_content(contract_addon_reference):
    contract_addon = AddonListService.get_filtered_objects(current_user, addon_reference=contract_addon_reference)
    if not contract_addon.first():
        raise NotFound
    
    contract_addon = contract_addon.first()

    all_devices = DeviceListService.get_non_used_devices_for_user_list(current_user, add_on_offer=contract_addon.offer_version.offer)

    show_nonpayg = should_show_auto_generated_nonpayg(
        addon_offer=contract_addon.offer_version.offer
    )
    select2 = {
        'all_devices': {
            'items': all_devices,
            'id': 'composed_serial',
            'text': 'composed_serial',
            'data': {
                'apitype': 'api_type'
            },
            'raw_format': True,
            'url': url_for('transaction_request.swap_addon_device_transaction_content', contract_addon_reference=contract_addon_reference)
        }
    }

    return render(
        'swap_addon_device_transaction_content.html',
        contract_reference=contract_addon.reference,
        current_device=contract_addon.device.composed_serial if contract_addon.device else '',
        select2=select2,
        show_nonpayg=show_nonpayg
    ) 