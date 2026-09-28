from datetime import datetime
from payg_loan_system.contracts.models.contract_event_model import ContractEvent, ContractEventType
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.offers.services.offer_entity_restriction_service import OfferEntityRestrictionService
from shared.services.settings_service import SettingsService


class ContractChangeService:

    @classmethod
    def change_contract_offer(cls, contract, new_offer, approver, note=None):
        error = cls._check_if_offer_change_possible(contract, new_offer)
        if error:
            return error

        total_paid = contract.get_cumulative_amount_repaid() + contract.pending_amount

        old_offer = contract.offer
        contract.offer = new_offer

        contract_event = ContractEvent(
            contract=contract,
            time=datetime.now(),
            type=ContractEventType.offer_change,
            old_offer=old_offer,
            new_offer=new_offer,
            approver=approver,
            note=note if note else ''
        )
        repayments = [ContractRepaymentService.create_adjustment_after_offer_change(contract)]
        if not contract.status == ContractStatus.completed:
            repayments += ContractRepaymentService.repay_and_reconcile(contract)
        # We do that to clear pending payments that would be over the new amount due if any
        ContractRepaymentService.clear_pending_payment_if_needed(contract)
        newly_discounted = sum([r.amount_discounted for r in repayments])

        assert total_paid == contract.get_cumulative_amount_repaid() + contract.pending_amount - newly_discounted

        contract.update_cached_data(contract_terms_changed=True, volatile=True)
        return {'success': True, 'contract_event_id': contract_event.id, 'repayments': repayments}

    @classmethod
    def _check_if_offer_change_possible(cls, contract, new_offer):
        if new_offer == None:
            return {'success': False,
                    'status': 'OFFER_DOES_NOT_EXIST'}
        if contract.offer == new_offer:
            return {'success': False,
                    'status': 'DEVICE_ALREADY_ON_OFFER',
                    'offer_code': new_offer.code}
        if not new_offer.in_use_for_new_clients:
            return {'success': False,
                    'status': 'OFFER_DISABLED'}
        device_error = cls._check_device_compatible_with_new_offer(contract, new_offer)
        if device_error:
            return device_error
        if new_offer.type != contract.offer.type:
            return {'success': False,
                    'status': 'OFFER_OF_DIFFERENT_TYPE'}
        if not OfferEntityRestrictionService.is_offer_allowed_for_contract(
            new_offer, contract.client.person.village
        ):
            return {'success': False,
                    'status': 'OFFER_NOT_AVAILABLE_IN_ENTITY'}
        total_paid_old_offer = contract.get_cumulative_amount_repaid()
        new_offer_deposit = new_offer.registration_fee
        if total_paid_old_offer < new_offer_deposit:
            return {'success': False,
                    'status': 'OFFER_CHANGE_FAILED_AMOUNT_PAID_BELOW_DEPOSIT'}
        new_offer_value = new_offer.get_total_value_with_deposit()+contract.get_total_extended()
        if contract.can_be_completed and new_offer_value < total_paid_old_offer:
            return {'success': False,
                    'status': 'OFFER_CHANGE_FAILED_AMOUNT_PAID_ABOVE_NEW_VALUE'}
        return None

    @staticmethod
    def _offer_requires_linked_device(offer):
        if SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device':
            return False
        return bool(offer.linked_to_product)

    @classmethod
    def _check_device_compatible_with_new_offer(cls, contract, new_offer):
        linked_device = contract.linked_device
        if linked_device:
            if not linked_device.can_use_offer(new_offer):
                return {'success': False, 'status': 'DEVICE_NOT_ALLOWED_ON_OFFER'}
            return None
        if cls._offer_requires_linked_device(new_offer):
            return {'success': False, 'status': 'CONTRACT_HAS_NO_DEVICE'}
        return None
