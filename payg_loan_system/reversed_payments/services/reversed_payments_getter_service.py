from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from payg_loan_system.reversed_payments.models import ReversedPayment
from shared.services.base_getter_service import BaseGetterService


class ReversedPaymentGetterService(BaseGetterService):

    OBJ_NAME = 'Reversed Payment'

    @classmethod
    def get_from_filtered_view(cls, user, view=None, entity=None, status=None, **kwargs):

        extra = {}
        if view == 'managed_by_me':
            extra = dict(managed_by=user)
        elif view == 'orphaned':
            extra = dict(filter="orphaned")

        handled = None
        if status == 'handled':
            handled = True
        elif status in ['unhandled', 'default']:
            handled = False

        extra.update(kwargs)

        reversed_payments = cls.get_list(user, entity=entity, handled=handled, **extra)

        return reversed_payments

    @classmethod
    def get_filtered_objects(cls, current_user=None, entity=None, filter=None,
        managed_by=None, handled=None, **kwargs):
        payments = PaymentGetterService.get_list(
            current_user, entity=entity, filter=filter,
            managed_by=managed_by, extra_permission="ViewReversedPayments",
            from_date=kwargs.get('from_payment_date'),
            to_date=kwargs.get('to_payment_date'),
            search=kwargs.get('search_transaction_id'),
            memo=kwargs.get('memo')
        )
        reversals = ReversedPayment.select(lambda r: r.payment in payments)
        if handled is not None:
            reversals = reversals.filter(lambda r: r.handled == handled)
        search = kwargs.get('search_reversal_id')
        if search:
            reversals = reversals.filter(lambda r: search.lower() in r.reference_code.lower())
        from_date = kwargs.get('from_reversal_date')
        if from_date:
            reversals = reversals.filter(lambda r: r.reversed_on >= from_date)
        to_date = kwargs.get('to_reversal_date')
        if to_date:
            reversals = reversals.filter(lambda r: r.reversed_on < to_date)
        approver = kwargs.get('approver')
        if approver:
            reversals = reversals.filter(lambda r: r.user == approver)
        return reversals
