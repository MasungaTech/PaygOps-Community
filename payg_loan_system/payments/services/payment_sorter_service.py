from payg_loan_system.contracts.models.reconciled_payment_model import ReconciledPayment
from shared.services.sorter import Sorter
from payg_loan_system.payments.models.payment import Payment
from pony import orm


class CashCollectedSorter(Sorter):
    def sort_by(field_name):
        options = {
            'id': CashCollectedSorter.by_id,
            'amount': CashCollectedSorter.by_amount,
            'received_on': CashCollectedSorter.by_received_on,
            'reference': CashCollectedSorter.by_reference,
            'paycash_reference': CashCollectedSorter.by_paycash_reference,
            'mentors': CashCollectedSorter.by_mentors,
            'clients': CashCollectedSorter.by_clients}

        return options.get(field_name, CashCollectedSorter.by_amount)

    def real_field_sort(field_name, desc=False):
        options = {
            'id': Payment.id,
            'amount': Payment.Amount,
            'received_on': Payment.PaymentReceptionTime,
            'reference': Payment.Reference,
            'paycash_reference': lambda p: p.back_payment.Reference,
            'mentors': False,
            'clients': False
        }
        options_desc = {
            'paycash_reference': lambda p: orm.desc(p.back_payment.Reference),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, Payment.PaymentReceptionTime))
        return options.get(field_name, Payment.PaymentReceptionTime)

    @staticmethod
    def by_amount(object):
        return object.Amount

    @staticmethod
    def by_received_on(object):
        return object.PaymentTime

    @staticmethod
    def by_reference(object):
        return object.Reference

    @staticmethod
    def by_paycash_reference(object):
        return object.back_payment.Reference

    @staticmethod
    def by_mentors(object):
        return object.PaymentWallet.user.full_name

    @staticmethod
    def by_clients(object):
        return object.client.full_name if object.client else ''


class PaymentSorter(Sorter):
    def sort_by(field_name):
        options = {
            'id': PaymentSorter.by_id,
            'amount': PaymentSorter.by_amount,
            'received_on': PaymentSorter.by_reception_time,
            'reference': PaymentSorter.by_reference,
            'clients': PaymentSorter.by_clients,
            'balance': PaymentSorter.by_balance,
            'source': PaymentSorter.by_source,
        }

        return options.get(field_name, PaymentSorter.by_reception_time)

    @staticmethod
    def real_field_sort(field_name, desc=False):
        options = {
            'id': Payment.id,
            'amount': Payment.Amount,
            'received_on': Payment.PaymentReceptionTime,
            'reference': Payment.Reference,
            'clients': False,
            'balance': False,
            'source': lambda P: P.PaymentWallet.Type
        }
        options_desc = {
            'source': lambda P: orm.desc(P.PaymentWallet.Type)
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, Payment.PaymentReceptionTime))
        return options.get(field_name, Payment.PaymentReceptionTime)

    @staticmethod
    def by_amount(object):
        return object.Amount

    @staticmethod
    def by_reception_time(object):
        return object.PaymentReceptionTime

    @staticmethod
    def by_reference(object):
        return object.Reference

    @staticmethod
    def by_clients(object):
        if object.PaymentWallet.client:
            return object.PaymentWallet.client.person.name
        else:
            return object.PaymentWallet.FullName

    @staticmethod
    def by_balance(object):
        return object.PaymentWallet.get_balance()

    @staticmethod
    def by_source(object):
        return object.PaymentWallet.Type


class ReconciledPaymentSorter(Sorter):

    def sort_by(field_name):
        options = {
            'id': ReconciledPaymentSorter.by_id,
            'amount': ReconciledPaymentSorter.by_amount,
            'date': ReconciledPaymentSorter.by_reception_time,
            'type': ReconciledPaymentSorter.by_type,
        }

        return options.get(field_name, ReconciledPaymentSorter.by_reception_time)

    @staticmethod
    def real_field_sort(field_name, desc=False):
        options = {
            'id': ReconciledPayment.id,
            'amount': ReconciledPayment.amount,
            'date': ReconciledPayment.time,
            'type': ReconciledPayment.type,
        }
        return options.get(field_name, ReconciledPayment.time)

    @staticmethod
    def by_amount(object):
        return object.amount

    @staticmethod
    def by_reception_time(object):
        return object.time

    @staticmethod
    def by_type(object):
        return object.type

