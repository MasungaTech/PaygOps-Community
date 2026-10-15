from datetime import datetime
from shared.services.sorter import Sorter


class ReversedPaymentSorter(Sorter):
    def sort_by(field_name):
        options = {
            'id': ReversedPaymentSorter.by_id,
            'amount': ReversedPaymentSorter.by_amount,
            'memo': ReversedPaymentSorter.by_memo,
            'reversed_on': ReversedPaymentSorter.by_reversed_on,
            'payment_date': ReversedPaymentSorter.by_payment_date,
            'handled': ReversedPaymentSorter.by_handled,
        }

        return options.get(field_name, ReversedPaymentSorter.by_handled)

    @staticmethod
    def by_reversed_on(object):
        return object.reversed_on or datetime.max

    @staticmethod
    def by_amount(object):
        return getattr(object.payment, 'Amount', object.amount or 0)

    @staticmethod
    def by_payment_date(object):
        return getattr(object.payment, 'PaymentTime', datetime.min)

    @staticmethod
    def by_memo(object):
        return getattr(object.payment, 'memo', '')

    @staticmethod
    def by_handled(object):
        return object.handled
