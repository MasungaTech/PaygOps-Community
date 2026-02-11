from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from pony.orm import select
from flask import flash

from payg_loan_system.reversed_payments.models import ReversedPayment
from core_system.client.services.client_getter_service import ClientGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService


class PaymentReversalFilter:
    @classmethod
    def filter_by_path(cls, user, path):

        if path == 'unhandled':
            payment_reversals = UnhandledPaymentReversal(user).filter()
        elif path == 'handled':
            payment_reversals = ReversedPayment.all_handled()
        elif path == 'myshop':
            payment_reversals = MyHubPaymentReversal(user).filter()
        elif path == 'orphaned':
            if not user.can_access('ViewOrphanedPayments'):
                flash('You do not have the authorization to see orphaned payments. ')
            payment_reversals = OrphanedPaymentReversal(user).filter()
        else:
            payment_reversals = AllPaymentReversal(user).filter()

        return payment_reversals


class FilterInterface:
    def __init__(self, user):
        self.user = user

    def filter(self):
        if self._check_permission():
            return self._filter()
        return []

    def _check_permission(self):
        return self.user.can_access(self.PERMISSION)


class OrphanedPaymentReversal(FilterInterface):
    PERMISSION = 'ViewClients'

    def _filter(self):
        orphaned_reversed_payment = select(reversed for reversed in ReversedPayment if reversed.payment is None
                                           or reversed.payment.PaymentWallet.client.person == self.user.person)
        return orphaned_reversed_payment


class MyHubPaymentReversal(FilterInterface):
    PERMISSION = 'ViewClients'

    def _filter(self):
        clients_in_my_hub = ClientGetterService.get_clients_in_user_shop(self.user)
        leads_in_my_hub = LeadGetterService.get_leads_in_user_shop(self.user)
        reversed_in_my_hub = select(reversed for reversed in ReversedPayment if reversed.payment.PaymentWallet.client in clients_in_my_hub or
                                    reversed.payment.PaymentWallet.lead in leads_in_my_hub)
        orphaned_reversed_payment = select(reversed for reversed in ReversedPayment if reversed.payment is None
                                           or reversed.payment.PaymentWallet.client.person == self.user.person)
        reversed_in_hub_without_orphaned = reversed_in_my_hub.filter(lambda reversed: reversed not in orphaned_reversed_payment)

        return reversed_in_hub_without_orphaned


class AllPaymentReversal:
    def __init__(self, user):
        self.user = user

    def filter(self):
        payments = PaymentGetterService.get_list(self.user)
        return ReversedPayment.select(lambda rp: rp.payment in payments)


class UnhandledPaymentReversal:
    def __init__(self, user):
        self.user = user

    def filter(self):
        unhandled_payment_reversal = ReversedPayment.all_unhandled()
        all_payment_for_user = AllPaymentReversal(self.user).filter()
        return unhandled_payment_reversal.filter(lambda payment_reversal: payment_reversal in all_payment_for_user)
