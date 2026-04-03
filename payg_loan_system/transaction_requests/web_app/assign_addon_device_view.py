from flask import url_for
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound
from pony.orm import db_session
from shared.helpers.select2 import render
from shared.helpers.authorizer import authorizer
from shared.services.settings_service import SettingsService
from payg_loan_system.devices.device_list_service import DeviceListService
from payg_loan_system.contracts.services.addon_list_service import AddonListService
from . import transaction_request


@transaction_request.route('/assign_addon_device/content/<string:contract_addon_reference>', methods=['GET'])
@login_required
@authorizer('SwapDeviceActions')
@db_session
def assign_addon_device_transaction_content(contract_addon_reference):
    contract_addon = AddonListService.get_filtered_objects(current_user, addon_reference=contract_addon_reference)
    if not contract_addon.first():
        raise NotFound
    
    contract_addon = contract_addon.first()

    all_devices = DeviceListService.get_non_used_devices_for_user_list(current_user, add_on_offer=contract_addon.offer_version.offer)

    if contract_addon.offer_version.offer.product_type:
        show_nonpayg = False
    else:
        show_nonpayg = SettingsService.get_setting('NPGDeviceEnabled')

    select2 = {
        'all_devices': {
            'items': all_devices,
            'id': 'composed_serial',
            'text': 'composed_serial',
            'data': {
                'apitype': 'api_type'
            },
            'raw_format': True,
            'url': url_for('transaction_request.assign_addon_device_transaction_content', contract_addon_reference=contract_addon_reference)
        }
    }

    return render(
        'assign_new_addon_device_transaction_content.html',
        contract_reference=contract_addon.reference,
        select2=select2,
        show_nonpayg=show_nonpayg
    ) 