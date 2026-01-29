from datetime import datetime
from payg_loan_system.contracts.models.addons_model import AddOnType
from payg_loan_system.contracts.models.reconciled_payment_model import ReconciledPayment
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.logger.loggers import Error
from pony import orm
from core_system.core_entities import db

from shared.services.base_getter_service import BaseGetterService
from shared.services.settings_service import SettingsService


class ReconciledPaymentService(BaseGetterService):

    OBJ_NAME = 'Reconciled Payment'

    REVERSAL_TYPES = {
        ReconciledPaymentType.repayment: ReconciledPaymentType.repayment_reversal,
        ReconciledPaymentType.initial_payment: ReconciledPaymentType.downpayment_reversal,
        ReconciledPaymentType.repayment_pending: ReconciledPaymentType.repayment_pending_reversal,
        ReconciledPaymentType.addon: ReconciledPaymentType.addon_payment_reversal,
        ReconciledPaymentType.payment_pending_reconciliation: ReconciledPaymentType.payment_pending_reconciliation_reversal,
        ReconciledPaymentType.blocked_during_lead_editing: ReconciledPaymentType.blocked_during_lead_editing_reversal,
        ReconciledPaymentType.user: ReconciledPaymentType.user_reversal,
        ReconciledPaymentType.payment_to_client: ReconciledPaymentType.payment_client_reversal
    }

    @classmethod
    def create_reconciliation(cls, repayment_amount=None, lead=None, addon=None, contract_pending_repayment=None,
                              user=None, type=None, payment=None, account=None, amount=None, note='', person=None, time=None, origin_reconciled_payment=None):

        assert payment or (account and amount is not None), \
            "A valid source is required (either payment or account and amount)"
        assert type == ReconciledPaymentType.manual_adjustment or repayment_amount or lead or addon or contract_pending_repayment or user or person, \
            "A valid destination is required (repayment, lead, addon, user, person - overpaid client - or contract - for pending -)"

        account = payment.PaymentWallet if payment else account
        amount = min(payment.remaining, payment.PaymentWallet.balance) if payment and not amount else amount

        type = cls._get_type_if_missing(type, repayment_amount, addon, contract_pending_repayment, user, person)
        amount = cls._calculate_amount_to_reconcile(type, repayment_amount, amount, lead, addon)
        if amount > account.get_balance() and not SettingsService.get_setting('FeatureToggles').get('OffTaking', False):
            raise Error(
                'There is not sufficient balance to use that amount',
                code='AMOUNT_OVER_BALANCE',
                balance=account.get_balance(),
                amount=amount
            )
        
        assert type == ReconciledPaymentType.manual_adjustment or amount != 0, "You cannot create a reconciliation with 0 value"
        return cls._create_reconciled_payment_object(time, lead, addon, contract_pending_repayment, user, type, payment, account, amount, note, person, origin_reconciled_payment)
    
    @classmethod
    def _delete_from_object_and_user(cls, reconciled_payment, user):
        cls.revert(reconciled_payment, user=user)

    @classmethod
    def get_filtered_objects(cls, current_user, addon=None, addon_reference=None, contract=None, lead=None, type=None, include_reversed=False, client_id=None, from_date=None, to_date=None, **kwargs):
        recons = ReconciledPayment.select() if include_reversed not in ['false', 'False', False, 0, '', [], None] else ReconciledPayment.select(lambda r: not r.converse)
        if addon:
            recons = recons.filter(lambda r: addon == r.add_on.id)
        if addon_reference:
            recons = recons.filter(lambda r: addon_reference in r.add_on.reference)
        if contract:
            contracts1 = recons.filter(lambda r: contract in r.repayment.contract.reference)
            contracts2 = recons.filter(lambda r: contract in r.contract_pending_repayment.reference)
            contracts3 = recons.filter(lambda r: contract in r.lead.future_contract_reference)
            recons = recons.filter(lambda r: r in contracts1 or r in contracts2 or r in contracts3)
        if type:
            recons = recons.filter(lambda r: r.type in type.split(','))
        if lead:
            recons = recons.filter(lambda r: r.lead.id == lead)
        if client_id:
            recons = recons.filter(lambda r: r.person.client.id == client_id)
        if from_date:
            recons = recons.filter(lambda r: r.time >= from_date)
        if to_date:
            recons = recons.filter(lambda r: r.time < to_date)
        return recons

    @classmethod
    def revert(cls, reconciled_payment, time=None, user=None, cancelling=False):
        note = f'Manually reversed by {user.full_name} ({user.id})' if user else ''
        if reconciled_payment.converse:
            raise Error('Reconciled Payment already reverted')
        repayment = reconciled_payment.repayment
        if repayment:
            if not repayment.converse:
                raise Error('You cannot revert a reconciled payment linked to a repayment directly, please revert the repayment.')
            repayment = repayment.converse
        if not cancelling and reconciled_payment.add_on and reconciled_payment.add_on.contract.downpayment_fully_paid and not reconciled_payment.add_on.time_canceled:
            if reconciled_payment.add_on.offer_version.offer.type == AddOnType.deposit_change:
                raise Error('You cannot revert a reconciled payment linked to a Deposit Change add-on. Please consider reverting the downpayment.')
            else:
                raise Error('You cannot revert a reconciled payment linked to an add-on.')
        ReconciledPayment(
            time=time or datetime.now(),
            amount=-reconciled_payment.amount,
            payment_account=reconciled_payment.payment_account,
            linked_payment=reconciled_payment.linked_payment,
            type=cls.REVERSAL_TYPES[reconciled_payment.type],
            lead=reconciled_payment.lead,
            user=reconciled_payment.user,
            add_on=reconciled_payment.add_on,
            repayment=repayment,
            note=note,
            contract_pending_repayment=reconciled_payment.contract_pending_repayment,
            person=reconciled_payment.person,
            converse=reconciled_payment
        )

    @staticmethod
    def _get_type_if_missing(type, repayment_amount, addon, contract_pending, user, person):
        if not type and repayment_amount:
            return ReconciledPaymentType.repayment
        if not type and contract_pending:
            return ReconciledPaymentType.repayment_pending
        if not type and addon:
            return ReconciledPaymentType.addon
        if not type and user:
            return ReconciledPaymentType.user
        if not type and person:
            return ReconciledPaymentType.payment_pending_reconciliation
        return type

    @staticmethod
    def _calculate_amount_to_reconcile(type, repayment_amount, amount, lead, addon):
        missing_in_repayment = repayment_amount if repayment_amount else float('inf')
        lead_has_maximum = type == ReconciledPaymentType.repayment_pending and lead and lead.offer and lead.offer.can_be_completed
        maximum_lead = lead.maximum_pending if lead_has_maximum else float('inf')
        remaining_lead = lead.left_to_pay if lead and type == ReconciledPaymentType.initial_payment else maximum_lead
        remaining_addon = addon.to_pay if addon and type == ReconciledPaymentType.addon else float('inf')
        return min(missing_in_repayment, amount, remaining_lead, remaining_addon)

    @staticmethod
    def _create_reconciled_payment_object(time, lead=None, addon=None, contract_pending_repayment=None,
                                          user=None, type=None, payment=None, account=None, amount=None, note='', person=None, origin_reconciled_payment=None):
        r = ReconciledPayment(
            time=time or datetime.now(),
            amount=amount,
            payment_account=account,
            linked_payment=payment,
            type=type,
            lead=lead,
            user=user,
            note=note,
            contract_pending_repayment=contract_pending_repayment,
            add_on=addon,
            person=person,
            origin_reconciled_payment=origin_reconciled_payment
        )
        orm.flush()  # this shouldn't be here
        add_hook_after_commit(db, 'new_reconciliation', r.get_serialized_object())
        return r