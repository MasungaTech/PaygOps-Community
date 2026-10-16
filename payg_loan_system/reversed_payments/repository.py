from pony.orm import db_session, exists, commit, count, IntegrityError, TransactionIntegrityError, CacheIndexError

from payg_loan_system.reversed_payments.models import ReversedPayment
from payg_loan_system.payments.models.payment import Payment

from shared.logger.loggers import LogAPI, Error

log = LogAPI()


class PaymentReversalRepository:

    @classmethod
    @db_session
    def save(cls, payment_reversal):
        descriptor = payment_reversal.serialize()
        log.Event('Saving Payment Reversal: {}'.format(repr(descriptor)))
        try:
            reversed_payment = ReversedPayment(reference_code=descriptor['reference'],
                                               payment_code=descriptor['payment_reference'],
                                               reversed_on=descriptor['sent_datetime'],
                                               wallet_operator=descriptor['wallet_operator'])
            reversed_payment = cls._add_optional_fields(reversed_payment, descriptor)
            commit()
        except (IntegrityError, TransactionIntegrityError, CacheIndexError) as e:
            raise Error('Duplicated reversal reference '+descriptor['reference'])
        log.Event('Payment Reversal successfully saved. ID: {}'.format(reversed_payment.id))
        return reversed_payment

    @staticmethod
    @db_session
    def get_by_reference(reference):
        return ReversedPayment.get(reference_code=reference.strip())

    @classmethod
    @db_session
    def has_payment_related(cls, payment_reversal):
        descriptor = payment_reversal.serialize()
        payment_reference = descriptor['payment_reference']
        wallet_operator = descriptor['wallet_operator']
        payment_and_wallet = exists(payment for payment in Payment if (payment.Reference == payment_reference) and (payment.wallet_operator == wallet_operator))
        return payment_and_wallet or not wallet_operator and Payment.select(lambda p: p.Reference == payment_reference).count() == 1

    @classmethod
    @db_session
    def link_to_payment(cls, payment_reversal):
        descriptor = payment_reversal.serialize()

        payment_reversal_reference = descriptor['reference']
        payment_reversal_instance = cls.get_by_reference(payment_reversal_reference)
        payment_reference = descriptor['payment_reference']
        wallet_operator = descriptor['wallet_operator']
        payment = Payment.get(Reference=payment_reference, wallet_operator=wallet_operator)
        if not payment and not wallet_operator:
            payment = Payment.get(Reference=payment_reference)

        payment.reversed_payment = payment_reversal_instance
        log.Event('Linked payment reversal "{}" to payment reference "{}"'.format(payment_reversal_reference, payment_reference))

    @staticmethod
    @db_session
    def _add_optional_fields(reversed_payment, data):
        sender_msisdn = data.get('sender_msisdn', None)
        sender_name = data.get('sender_name', None)
        amount = data.get('amount', None)

        if sender_msisdn:
            reversed_payment.sender_msisdn = sender_msisdn
        if sender_name:
            reversed_payment.sender_name = sender_name
        if amount:
            reversed_payment.amount = amount
        return reversed_payment
