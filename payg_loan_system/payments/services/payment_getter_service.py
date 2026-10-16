

from pony.orm import left_join, select

from payg_loan_system.contracts.models.reconciled_payment_model import \
    ReconciledPayment
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWalletType
from shared.services.base_getter_service import BaseGetterService


class PaymentGetterService(BaseGetterService):

    OBJ_NAME = 'Payment'

    SOURCE_MAP = {
        'mobile_money': [PaymentWalletType.mobile_money],
        'cash': [PaymentWalletType.cash],
        '': [PaymentWalletType.mobile_money, PaymentWalletType.cash]
    }

    @classmethod
    def get_from_filtered_view(cls, user, view=None, entity=None, portfolio=None, search=None, client_group=None, client=None,
        source='', wallet=None, from_date=None, to_date=None, wallet_operator=None, user_collecting=None, memo=None, phone_number=None, tab=None):

        extra = {}
        if view == 'managed_by_me':
            extra = dict(managed_by=user)
        elif view == 'orphaned':
            extra = dict(filter="orphaned")

        payments = cls.get_list(user, search=search, entity=entity, portfolio=portfolio, client_group=client_group, client=client, 
            source=source, wallet=wallet, from_date=from_date, to_date=to_date, wallet_operator=wallet_operator, user_collecting=user_collecting, memo=memo, phone_number=phone_number, **extra)

        if tab == 'incoming':
            payments = payments.filter(lambda p: p.Amount >= 0)
        elif tab == 'outgoing':
            payments = payments.filter(lambda p: p.Amount < 0)

        return payments

    @classmethod
    def get_filtered_objects(cls, current_user, filter=None, agent_wallet=None, from_date=None, to_date=None,
        source=None, cached=True, entity=None, portfolio=None, client=None, agent=None, wallet=None, search=None,
        managed_by=None, extra_permission=None, wallet_operator=None, user_collecting=None, memo=None, phone_number=None, reconciling=False, **kwargs):

        if filter == 'orphaned':
            if current_user.can_access('ViewOrphanedPayments'):
                payments = select(p for p in Payment if p.orphaned_cached and p.PaymentWallet.cached_balance_positive)
            else:
                payments = select(p for p in Payment if p.id == -1)
        else:
            if current_user.can_access('ViewOrphanedPayments') and current_user.can_access_in_all('ViewPayments'):
                payments = select(p for p in Payment)
            else:
                # We dont include orphaned payments in the "all" if the user cant see all payments 
                # to preserve old behaviour and performance (the alternitve is VERY slow)
                villages_ids, client_groups_ids = current_user.get_villages_and_client_groups_with_permission('ViewPayments', return_villages_ids=True)
                if client_groups_ids:
                    unique_linked_payments_ids = left_join(r.linked_payment.id for r in ReconciledPayment if r.cached_person.village.id in villages_ids or r.cached_person.client_group.id in client_groups_ids)
                else:
                    unique_linked_payments_ids = left_join(r.linked_payment.id for r in ReconciledPayment if r.cached_person.village.id in villages_ids)
                linked_payments = select(p for p in Payment if p.id in unique_linked_payments_ids)
                # We only get the orphaned payments in that case when reconciling otherwise it's VERY slow
                if not reconciling:
                    payments = linked_payments
                else:
                    if current_user.can_access('ViewOrphanedPayments') or False:
                        payments = select(p for p in Payment if p in linked_payments or p.orphaned_cached and p.PaymentWallet.cached_balance_positive)
                    else:
                        payments = select(p for p in Payment if p in linked_payments)
        if entity:
            villages = select(e for e in entity.descendants)
            linked_payments = left_join(r.linked_payment for r in ReconciledPayment if r.cached_person.village in villages)
            payments = select(p for p in Payment if p in linked_payments)
        if agent_wallet is False:
            payments = payments.filter(lambda p: p.PaymentWallet.Type != PaymentWalletType.agent_collection)
        if agent_wallet is True:
            payments = payments.filter(lambda p: p.PaymentWallet.Type == PaymentWalletType.agent_collection)
        if agent:
            payments = payments.filter(lambda p: p.PaymentWallet.user == agent)
        if wallet:
            payments = payments.filter(lambda p: p.PaymentWallet == wallet)
        ptype = cls.SOURCE_MAP.get(source)
        if ptype:
            payments = payments.filter(lambda p: p.PaymentWallet.Type in ptype)
        if search:
            back_payments = payments.filter(lambda p: search.lower() in p.back_payment.Reference)
            payments = payments.filter(lambda p: search.lower() in p.Reference.lower() or p in back_payments)
        if memo:
            payments = payments.filter(lambda p: memo.lower() in p.memo.lower())
        if phone_number:
            phone_number = phone_number.replace('+', '')
            payments = payments.filter(lambda p: phone_number in p.PaymentWallet.phone_number.number)
        if from_date:
            payments = payments.filter(lambda p: p.PaymentReceptionTime >= from_date)
        if to_date:
            payments = payments.filter(lambda p: p.PaymentReceptionTime < to_date)
        if client:
            reconciled = select(r.linked_payment for r in ReconciledPayment if r.cached_person == client.person)
            payments = payments.filter(lambda p: p in reconciled)
        if user_collecting:
            payments = payments.filter(lambda p: p.back_payment.PaymentWallet.user.id == user_collecting.id)
        if wallet_operator:
            if wallet_operator == 'Empty': wallet_operator = ''
            payments = payments.filter(lambda p: p.wallet_operator == wallet_operator)

        return payments

    @classmethod
    def get_reconciled_payments_from_clients_and_leads_in_entities(cls, villages, client_groups_ids=None, from_date=None, to_date=None):
        if client_groups_ids:
            payments = select(r for r in ReconciledPayment if not r.user and (r.cached_person.village.id in villages or r.cached_person.client_group.id in client_groups_ids))
        else:
            payments = select(r for r in ReconciledPayment if not r.user and r.cached_person.village.id in villages)
        if from_date:
            payments = payments.filter(lambda r: r.time >= from_date)
        if to_date:
            payments = payments.filter(lambda r: r.time < to_date)
        return payments.filter(lambda r: r.payment_account.Type != PaymentWalletType.agent_collection)
