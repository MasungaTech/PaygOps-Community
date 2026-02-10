from flask import flash, url_for
from flask_login import login_required, current_user
from pony.orm import db_session
from core_system.client.services.client_getter_service import ClientGetterService
from shared.helpers.select2 import render
from shared.helpers.authorizer import authorizer
from shared.services.settings_service import SettingsService
from tests.support.mock_query import MockQuery
from constants import NON_PAYG_TYPE
from . import transaction_request
from payg_loan_system.devices.device_list_service import DeviceListService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from werkzeug.exceptions import NotFound



@transaction_request.route('/undo_default/content/', methods=['GET'])
@transaction_request.route('/undo_default/content/client/<int:client_id>', methods=['GET'])
@transaction_request.route('/undo_default/content/<contract_reference>', methods=['GET'])
@transaction_request.route('/undo_default/content/contract/<int:contract_id>', methods=['GET'])
@login_required
@authorizer('UndoContractDefaultedActions')
@db_session
def undo_default_transaction_content(contract_reference=None, contract_id=None, client_id=None):
    this_contract = None
    all_contracts = None
    client_devices = None
    all_devices = None
    offer = None
    if contract_reference:
        this_contract = ContractGetterService.get_from_user_and_properties(current_user, reference=contract_reference, strict=True, main_resource=True)
        all_contracts = [this_contract]
        offer = this_contract.offer
    if contract_id:
        all_contracts = ContractGetterService.get_filtered_objects(current_user, id=contract_id)
        this_contract = all_contracts.first()
        if not this_contract: raise NotFound
        offer = this_contract.offer

    show_nonpayg = False
    if not contract_reference and not contract_id:
        if client_id:
            this_client = ClientGetterService.get_from_user_and_id(current_user, client_id, strict=True)
            all_contracts = this_client.contracts.select()
            if all_contracts.count() == 1:
                this_contract = all_contracts.first()
                offer = this_contract.offer
        else:
            all_contracts = ContractGetterService.get_list(current_user)
            
    show_nonpayg = SettingsService.get_setting('NPGDeviceEnabled') and (
        not offer or not offer.device_type or offer.device_type == NON_PAYG_TYPE)
    all_devices = DeviceListService.get_non_used_devices_for_user_list(current_user, offer)
    
    if this_contract and this_contract.linked_device:
        client_devices = MockQuery([this_contract.linked_device])
        
    select2 = {
        'all_devices': {
            'items': all_devices,
            'id': 'composed_serial',
            'text': 'composed_serial',
            'data': {
                'apitype': 'api_type'
            },
            'url': url_for(
                'transaction_request.undo_default_transaction_content',
                contract_reference=contract_reference,
                contract_id=contract_id,
                client_id=client_id
            ),
            'raw_format': True
        }
    }

    return render(
        'undo_default_transaction_content.html',
        this_contract=this_contract,
        contracts=all_contracts,
        select2=select2,
        client_devices=client_devices,
        show_nonpayg=show_nonpayg
    )
