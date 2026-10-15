from datetime import datetime, timedelta
from worker_app.tasks.try_reconcile_pending_payments import try_reconcile_pending_payments
from payg_loan_system.contracts.models.contract_event_model import ContractEvent, ContractEventType


class ContractEventService:

    @classmethod
    def create_contract_creation_event(cls, contract, approver, note=None):
        ContractEvent(
            contract=contract,
            time=contract.start_time,
            type=ContractEventType.creation,
            approver=approver,
            note=note if note else ''
        )

    @classmethod
    def create_contract_device_swap_event(cls, contract, approver, old_device, new_device, time=None, note=None):
        ContractEvent(
            contract=contract,
            time=time or datetime.now(),
            type=ContractEventType.device_swap,
            approver=approver,
            old_device=old_device,
            new_device=new_device,
            note=note if note else ''
        )

    @classmethod
    def create_contract_reference_price_change(cls, contract, approver, time=None, addons=None):
        ContractEvent(
            contract=contract,
            time=time or datetime.now(),
            type=ContractEventType.reference_pricing_change,
            old_offer=contract.offer,
            new_offer=contract.offer,
            approver=approver,
            addons=addons or []
        )
        try_reconcile_pending_payments(contract_id=contract.id) # done synchronously to avoid Updated Outside Transaction error

    @classmethod
    def create_contract_duration_change(cls, contract, approver, time=None, addons=None):
        ContractEvent(
            contract=contract,
            time=time or datetime.now(),
            type=ContractEventType.duration_change,
            old_offer=contract.offer,
            new_offer=contract.offer,
            approver=approver,
            addons=addons or []
        )
    
    @classmethod
    def create_contract_value_change(cls, contract, approver, time=None, addons=None):
        ContractEvent(
            contract=contract,
            time=time or datetime.now(),
            type=ContractEventType.value_change,
            old_offer=contract.offer,
            new_offer=contract.offer,
            approver=approver,
            addons=addons or []
        )
    
    @classmethod
    def create_contract_addon_device_event(cls, contract, approver, addon, time=None):
        ContractEvent(
            contract=contract,
            time=time or datetime.now(),
            type=ContractEventType.addon_device,
            approver=approver,
            new_device=addon.device,
            device_addon=addon
        )

    @classmethod
    def create_contract_addon_device_removal_event(cls, contract, approver, addon, time=None):
        ContractEvent(
            contract=contract,
            time=time or datetime.now(),
            type=ContractEventType.addon_device_removal,
            approver=approver,
            new_device=addon.device,
            device_addon=addon
        )

    @classmethod
    def create_contract_addon_device_swap_event(cls, contract, approver, old_device, new_device, addon, time=None, note=None):
        ContractEvent(
            contract=contract,
            time=time or datetime.now(),
            type=ContractEventType.addon_device_swap,
            approver=approver,
            old_device=old_device,
            new_device=new_device,
            device_addon=addon,
            note=note if note else ''
        )

    @classmethod
    def create_contract_addon_device_assign_event(cls, contract, approver, new_device, addon, time=None):
        """Creates an event for device assignment to contract addon"""
        ContractEvent(
            contract=contract,
            time=time or datetime.now(),
            type=ContractEventType.addon_device_assign,
            approver=approver,
            new_device=new_device,
            device_addon=addon
        )