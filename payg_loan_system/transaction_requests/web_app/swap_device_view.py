from flask import url_for
from flask_login import login_required, current_user
from pony.orm import db_session
from core_system.client.services.client_getter_service import ClientGetterService
from shared.helpers.select2 import render
from shared.helpers.authorizer import authorizer
from . import transaction_request
from payg_loan_system.devices.device_list_service import DeviceListService
from payg_loan_system.transaction_requests.nonpayg_device_picker import (
    should_show_auto_generated_nonpayg,
)
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from werkzeug.exceptions import NotFound


@transaction_request.route('/swap_device/content/contract/<int:contract_id>', methods=['GET'])
@transaction_request.route('/swap_device/content/<int:client_id>', methods=['GET'])
@login_required
@authorizer('SwapDeviceActions')
@db_session
def swap_device_transaction_content(client_id=None, contract_id=None):
    if client_id:
        this_client = ClientGetterService.get_from_user_and_id(current_user, client_id, strict=True, main_resource=True)
        contracts = this_client.contracts.select()
    else:
        contracts = ContractGetterService.get_filtered_objects(current_user, id=contract_id)
        if not contracts.first(): 
            raise NotFound
        this_client = contracts.first().client

    offer = this_client.contracts.select().first().offer if this_client.contracts.count() == 1 else None
    all_devices = DeviceListService.get_non_used_devices_for_user_list(current_user, offer)

    show_nonpayg = should_show_auto_generated_nonpayg(offer)

    select2 = {
        'all_devices': {
            'items': all_devices,
            'id': 'composed_serial',
            'text': 'composed_serial',
            'data': {
                'apitype': 'api_type'
            },
            'raw_format': True,
            'url': url_for('transaction_request.swap_device_transaction_content', client_id=client_id, contract_id=contract_id)
        }
    }

    return render(
        'swap_device_transaction_content.html',
        this_client=this_client,
        contracts=contracts,
        select2=select2,
        show_nonpayg=show_nonpayg
    )
