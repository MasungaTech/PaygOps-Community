from datetime import datetime
from messages_system.services.message_service import MessageService
from payg_loan_system.actions.activation import sync_activation
from payg_loan_system.actions.give_delay import handle_give_delay_request
from payg_loan_system.contracts.models.contract_event_model import ContractEvent, ContractEventType
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.offers.models import OfferType
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.helpers.date_helper import timedelta_to_hours
from shared.helpers.numbers import round_if_exists
from stock_management_system.services.stock_movement_creation_service import (
    StockMovementCreationService)
from stock_management_system.stock_status import StockMovementStatus, StockStatus
from core_system.core_entities import db
from shared.logger.loggers import Error

from pony.orm import desc
class ContractTerminationService:

    @classmethod
    def default_contract(cls, contract, approver, note=None):
        error = cls._check_if_termination_possible(contract)
        if error:
            return error

        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
        cls._create_contract_event_object(
            contract=contract,
            time=contract.end_time,
            type=ContractEventType.default,
            approver=approver,
            note=note if note else ''
        )

        cls._send_data_to_hook_defaulted(contract, approver)
        cls._update_contract_cache(contract)

        return {'success': True}

    @classmethod
    def repossess_device(cls, contract, approver, cancellation, note=None):
        error = cls._check_if_repossession_possible(contract, cancellation)
        if error:
            return error

        cls._create_contract_event_object(
            contract=contract,
            time=datetime.now(),
            type=ContractEventType.repossession,
            approver=approver,
            old_device=contract.linked_device,
            note=note if note else ''
        )
        contract.repossession_time = datetime.now()

        cls._send_data_to_hook_repossess(contract, approver)
        cls._update_contract_cache(contract)

        this_device = contract.linked_device
        this_device.contract = None
        this_device.ActiveUntil = None

        StockMovementCreationService.create(
            this_device.stock_item,
            StockStatus.with_user,
            user=approver,
            destination_user=approver,
            note="[Automatic] Repossession",
            manual=False
        )

        return {'success': True}

    @classmethod
    def cancel_contract(cls, contract, approver, note=None):

        contract.status = ContractStatus.cancelled
        contract.end_time = datetime.now()
        cls._create_contract_event_object(
            contract=contract,
            time=contract.end_time,
            type=ContractEventType.cancellation,
            approver=approver,
            note=note if note else ''
        )

        cls._send_data_to_hook_cancelled(contract, approver)
        cls._update_contract_cache(contract)

        return {'success': True}

    @classmethod
    def _update_contract_cache(cls, contract):
        contract.update_cached_data(contract_terms_changed=True, volatile=True)

    @classmethod
    def _check_if_termination_possible(cls, contract):
        if contract.status == ContractStatus.completed:
            return {'success': False, 'status': 'CONTRACT_ALREADY_COMPLETED'}
        if contract.status == ContractStatus.defaulted:
            return {'success': False, 'status': 'CONTRACT_ALREADY_DEFAULTED'}


    @classmethod
    def pause_contract(cls, contract, approver, note, send_sms):

        if contract.usage_based:
            raise Error('Unable to pause usage based contract')
        if contract.time_based and contract.offer.payment_day_of_month is not None:
            raise Error('Unable to pause subscription based contract with regular payment date enabled')
        if contract.status == ContractStatus.completed:
            raise Error('CONTRACT_ALREADY_COMPLETED')
        if contract.status == ContractStatus.defaulted:
            raise Error('CONTRACT_ALREADY_DEFAULTED')
        if contract.status == ContractStatus.paused:
            raise Error('CONTRACT_ALREADY_PAUSED')
        if contract.status == ContractStatus.cancelled:
            raise Error('CONTRACT_ALREADY_CANCELLED')
    
        contract.status = ContractStatus.paused
        cls._create_contract_event_object(
            contract=contract,
            time=datetime.now(),
            type=ContractEventType.pause,
            approver=approver,
            note=note or ''
        )

        cls._send_data_to_hook_paused(contract, approver)
        cls._update_contract_cache(contract)
        if send_sms:
            days_paid = round(contract.get_days_paid())
            days_to_pay = round(contract.get_days_to_pay())
            remaining_days_to_pay = round(contract.get_remaining_days_to_pay())
            weeks_paid = int(days_paid/7)
            days_paid = int(days_paid) - (weeks_paid * 7)
            weeks_to_pay = int(round(days_to_pay/7))
            remaining_weeks_to_pay = int(round(remaining_days_to_pay/7))
            sms_answer = {
                'status': 'CONTRACT_PAUSE_SUCCESS_SMS',
                'success': True,
                'name': contract.client.person.name,
                'surname': contract.client.person.surname,
                'contract_reference': contract.reference,
                'device_serial': contract.linked_device.get_display_name() if contract.linked_device else '',
                'offer_name': contract.offer.name,
                'already_paid': round_if_exists(sum(r.amount_paid for r in contract.repayments)),
                'remaining_due': round_if_exists(contract.get_outstanding_balance()),
                'total_to_pay': round_if_exists(contract.get_total_value()),
                'paid_so_far': round_if_exists(contract.get_cumulative_amount_repaid()),
                'remaining_due-pending_amount': round_if_exists(contract.pending_amount),
                'next_payment_price': round_if_exists(contract.next_payment_price()),
                'expected_paid': round_if_exists(contract.get_expected_amount_repaid()) or 0,
                'amount_in_arrears': round_if_exists(contract.get_net_cumulative_amount_in_arrears()) or 0,
                'expiration_time_day': contract.next_repayment_due_time,
                'remaining_days_to_pay': remaining_days_to_pay,
                'remaining_weeks_to_pay': remaining_weeks_to_pay,
                'weeks_to_pay': weeks_to_pay,
                'days_to_pay': days_to_pay,
                'paid_so_far+pending_amount': round_if_exists(contract.get_cumulative_amount_repaid() + contract.pending_amount),
            }
            MessageService.send_answer_to_person(person=contract.client.person, answer=sms_answer)
        return [{
            'status': 'CONTRACT_PAUSE_SUCCESS',
            'success': True,
            'contract_reference': contract.reference,
        }]

    @classmethod
    def resume_contract(cls, contract, approver, note=None):
        contract.status = ContractStatus.active
        resume_date = datetime.now()
        cls._create_contract_event_object(
            contract=contract,
            time=resume_date,
            type=ContractEventType.resume,
            approver=approver,
            note=note if note else ''
        )
        npdd = contract.next_repayment_due_time
        latest_pause_event = ContractEvent.select(lambda ce: ce.contract == contract and ce.type == ContractEventType.pause).order_by(desc(ContractEvent.time)).first()
        pause_date = latest_pause_event.time
        assert resume_date > pause_date, "Resume date must be after pause date"
        linked_device = contract.linked_device

        days_to_add = None
        # if NPDD < paused date, should be left unchanged
        if npdd > pause_date:
            base_date = max(resume_date, npdd) if contract.offer.forgive_lateness else npdd
            new_npdd = base_date + (min(npdd, resume_date) - pause_date)
            days_to_add = round(timedelta_to_hours(new_npdd - npdd)/24)
            
        this_client = contract.client
        if days_to_add:
            handle_give_delay_request(
                acting_user=approver,
                this_client=this_client,
                delayed_days=days_to_add,
                this_device=linked_device
            )

        cls._send_data_to_hook_resumed(contract, approver)
        cls._update_contract_cache(contract)

        answer = [{
            'status': 'CONTRACT_RESUME_SUCCESS',
            'success': True,
            'contract_reference': contract.reference,
        }]
        ContractRepaymentService.repay_and_reconcile(contract)
        return answer

    @classmethod
    def overpay_contract(cls, contract, approver, amount, repayment, note):
        if contract.status == ContractStatus.defaulted:
            raise Error('CONTRACT_ALREADY_DEFAULTED')
        if contract.status == ContractStatus.paused:
            raise Error('CONTRACT_ALREADY_PAUSED')
        if contract.status == ContractStatus.cancelled:
            raise Error('CONTRACT_ALREADY_CANCELLED')
        overpayment_time = datetime.now()
        cls._create_contract_event_object(
            contract=contract,
            time=overpayment_time,
            type=ContractEventType.overpayment,
            repayment=repayment,
            approver=approver,
            note=note if note else ''
        )
        contract.status = ContractStatus.overpaid
        cls._update_contract_cache(contract)
        this_client = contract.client
        formatted_data = {
            'contract_reference': contract.reference,
            'client_id': this_client.id,
            'name': this_client.person.name,
            'surname': this_client.person.surname,
            'overpaid_amount': amount,
            'acting_user_id': approver.id,
            'contract_event_id': ContractEvent.select(lambda ce: ce.contract == contract and ce.type == ContractEventType.overpayment).order_by(desc(ContractEvent.time)).first().id
        }
        add_hook_after_commit(db, 'contract_overpaid', formatted_data)


    @classmethod
    def _check_if_repossession_possible(cls, contract, cancellation):
        if not contract.linked_device:
            return {'success': False,
                    'status': 'CONTRACT_HAS_NO_DEVICE'}
        if contract.status != ContractStatus.defaulted and not cancellation:
            return {'success': False,
                    'status': 'CONTRACT_NOT_DEFAULTED'}
        return None

    @classmethod
    def _get_remaining_open_contract_count(cls, client):
        # We count the number of active contracts owned by the client
        active_contracts = 0
        for contract in client.contracts:
            if not contract.status == ContractStatus.defaulted:
                active_contracts += 1
        return active_contracts

    @classmethod
    def _send_data_to_hook_repossess(cls, contract, approver):
        client = contract.client
        device = contract.linked_device
        formatted_data = {
            'client_id': client.id,
            'client_name': client.person.name,
            'client_surname': client.person.surname,
            'device_serial_number': device.get_display_name(),
            'contract_reference': contract.reference,
            'remaining_device_count': cls._get_remaining_open_contract_count(client),
            'acting_user_id': approver.id
        }
        add_hook_after_commit(db, 'client_deregistered', formatted_data)

    @classmethod
    def _send_data_to_hook_defaulted(cls, contract, approver):
        client = contract.client
        formatted_data = {
            'client_id': client.id,
            'client_name': client.person.name,
            'client_surname': client.person.surname,
            'contract_reference': contract.reference,
            'acting_user_id': approver.id
        }
        add_hook_after_commit(db, 'contract_defaulted', formatted_data)

    @classmethod
    def _send_data_to_hook_cancelled(cls, contract, approver):
        client = contract.client
        formatted_data = {
            'client_id': client.id,
            'client_name': client.person.name,
            'client_surname': client.person.surname,
            'contract_reference': contract.reference,
            'acting_user_id': approver.id
        }
        add_hook_after_commit(db, 'contract_cancelled', formatted_data)

    @classmethod
    def _send_data_to_hook_paused(cls, contract, approver):
        client = contract.client
        formatted_data = {
            'client_id': client.id,
            'name': client.person.name,
            'surname': client.person.surname,
            'contract_reference': contract.reference,
            'acting_user_id': approver.id,
            'device_serial_number': contract.linked_device.get_display_name(),
            'contract_event_id': ContractEvent.select(lambda ce: ce.contract == contract and ce.type == ContractEventType.pause).order_by(desc(ContractEvent.time)).first().id
        }
        add_hook_after_commit(db, 'contract_paused', formatted_data)

    @classmethod
    def _send_data_to_hook_resumed(cls, contract, approver):
        client = contract.client
        formatted_data = {
            'client_id': client.id,
            'name': client.person.name,
            'surname': client.person.surname,
            'contract_reference': contract.reference,
            'acting_user_id': approver.id,
            'device_serial_number': contract.linked_device.get_display_name(),
            'contract_event_id': ContractEvent.select(lambda ce: ce.contract == contract and ce.type == ContractEventType.pause).order_by(desc(ContractEvent.time)).first().id
        }
        add_hook_after_commit(db, 'contract_resumed', formatted_data)

    @classmethod
    def _create_contract_event_object(cls, **kwargs):
        return ContractEvent(**kwargs)
