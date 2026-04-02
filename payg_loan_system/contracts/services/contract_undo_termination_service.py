from datetime import datetime
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.contract_event_model import ContractEvent, ContractEventType
from payg_loan_system.contracts.services.contract_creation_service import ContractCreationService
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from shared.services.settings_service import SettingsService
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from stock_management_system.services.stock_movement_creation_service import (
    StockMovementCreationService)
from stock_management_system.stock_status import StockStatus
from core_system.core_entities import db


class ContractUndoTerminationService:

    @classmethod
    def undo_default(cls, contract, approver, device=None, note=None):

        error = cls._check_if_undo_default_possible(contract, device)
        if error:
            return error

        was_repossessed = False
        old_device = contract.linked_device
        if device and contract.linked_device != device:
            was_repossessed = True
            if not StockMovementCreationService.user_can_make_action(device.stock_item, approver):
                return {
                    'success': False,
                    'status': 'STOCK_ITEM_NOT_VISIBLE',
                    'device_serial': device.get_display_name()
                }
            StockMovementCreationService.create(
                device.stock_item,
                StockStatus.installed,
                user=approver,
                destination_client=contract.client,
                note="[Automatic] Undo-Repossession",
                manual=False
            )
            cls._link_device_to_contract(device, contract)

        cls._undo_default_on_contract(contract)

        cls._create_contract_event_object(
            contract=contract,
            time=datetime.now(),
            type=ContractEventType.undo_default,
            approver=approver,
            old_device=old_device,
            new_device=contract.linked_device,
            note=note if note else ''
        )

        cls._send_data_to_hook_undo_default(contract, approver, was_repossessed)
        cls._update_contract_cache(contract)

        return {'success': True}

    @classmethod
    def _update_contract_cache(cls, contract):
        contract.update_cached_data(contract_terms_changed=True, volatile=True)

    @classmethod
    def _undo_default_on_contract(cls, contract):
        contract.status = ContractStatus.active
        contract.end_time = None
        contract.repossession_time = None

    @classmethod
    def _link_device_to_contract(cls, device, contract):
        ContractCreationService.link_device_to_contract(device, contract)
        ContractRepaymentService.sync_device_status_from_contract(device, contract)

    @classmethod
    def _check_if_undo_default_possible(cls, contract, this_device):
        if not this_device:
            this_device = contract.linked_device

        if contract.client.first_active_or_late_contract and not SettingsService.get_setting('AllowMultipleContracts'):
            return {'success': False,
                    'status': 'EXISTING_ACTIVE_CONTRACT'}

        if contract.linked_device and this_device != contract.linked_device:
            return {'success': False,
                    'status': 'CONTRACT_HAS_OTHER_DEVICE'}

        if contract.status != ContractStatus.defaulted:
            return {'success': False,
                    'status': 'CONTRACT_NOT_DEFAULTED'}

        if not this_device and SettingsService.get_setting('ContractDeviceRestrictions') != 'no_device' and contract.linked_device:
            return {'success': False,
                    'status': 'CONTRACT_HAS_NO_DEVICE'}
        if SettingsService.get_setting('ContractDeviceRestrictions') != 'no_device' and this_device:
            if this_device.contract is not None and this_device.contract != contract:
                answer = {'success': False,
                        'status': 'DEVICE_ALREADY_REGISTERED',
                        'device_owner_id': this_device.contract.client.id}
                return answer

            if not this_device.can_use_offer(contract.offer):
                answer = {'success': False,
                        'status': 'DEVICE_NOT_ALLOWED_ON_OFFER'}
                return answer

            if not this_device.is_compatible_with_offer(contract.offer):
                answer = {
                    'success': False,
                    'status': 'CREDIT_UNIT_NOT_ALLOWED_FOR_DEVICE',
                    'allowed_units': this_device.get_allowed_units()
                }
                return answer
        return None

    @classmethod
    def _send_data_to_hook_undo_default(cls, contract, approver, was_repossessed):
        client = contract.client
        device = contract.linked_device
        formatted_data = {
            'client_id': client.id,
            'client_name': client.person.name,
            'client_surname': client.person.surname,
            'device_serial_number': device.get_display_name() if device else None,
            'contract_reference': contract.reference,
            'was_repossessed': was_repossessed,
            'offer_code': contract.offer.code,
            'offer_type': contract.offer.get_human_readable_type(),
            'acting_user_id': approver.id
        }
        add_hook_after_commit(db, 'undo_contract_default', formatted_data)

    @classmethod
    def _create_contract_event_object(cls, **kwargs):
        return ContractEvent(**kwargs)

