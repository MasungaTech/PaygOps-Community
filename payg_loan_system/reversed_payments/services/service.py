from datetime import datetime
from payg_loan_system.contracts.models.reconciled_payment_model import ReconciledPayment
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService
from uuid import uuid1
from pony import orm
from payg_loan_system.reversed_payments.domain import PaymentReversal
from payg_loan_system.reversed_payments.models import ReversedPayment
from payg_loan_system.reversed_payments.repository import PaymentReversalRepository
from payg_loan_system.actions.collect_cash import generate_payment_reference
from payg_loan_system.transaction_requests.services.reverse_repayment_service import \
    ReverseRepaymentService
from sales_system.leads.services.edit_lead_service import EditLeadService
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService


class PaymentReversalService:

    @classmethod
    def process(cls, data):
        try:
            payment_reversal = PaymentReversal.deserialize(data)
            payment_reversal = cls._add_optional_fields(payment_reversal, data)

            existing = ReversedPayment.get(reference_code=payment_reversal.reference)
            if existing and cls.compare(existing, payment_reversal):
                return existing, 200
            reversal = PaymentReversalRepository.save(payment_reversal)

            if PaymentReversalRepository.has_payment_related(payment_reversal):
                PaymentReversalRepository.link_to_payment(payment_reversal)

            orm.commit()
            return reversal, 201
        except Exception as e:
            raise Error(f'Error processing reversal: {e}')
    
    @classmethod
    def compare(cls, existing, payment_reversal):
        data1 = existing.get_serialized_object()
        data2 = payment_reversal.serialize()
        return all([data1[k] == data2[k] for k in data1 if k != 'sent_datetime'])

    @classmethod
    def already_exists(cls, data):
        reversal = PaymentReversalRepository.get_by_reference(
            data.get('reversal_transaction_id', data.get('reference'))
        )
        if reversal:
            return True
        return False

    @classmethod
    def _add_optional_fields(cls, payment_reversal, data):
        sender_msisdn = data.get('wallet_msisdn', data.get('sender_msisdn', None))
        sender_name = data.get('wallet_name', data.get('sender_name', None))
        amount = data.get('amount', None)

        if sender_msisdn:
            payment_reversal.add_sender_msisdn(sender_msisdn)
        if sender_name:
            payment_reversal.add_sender_name(sender_name)
        if amount:
            payment_reversal.add_amount(amount)
        return payment_reversal

    @classmethod
    def user_permissions(cls, user):
        return {
            'show_hub': True,
            'show_orphaned': user.can_access('ViewOrphanedPayments')
        }

    @classmethod
    def reverse_payment(cls, payment, user=None):
        cls._check_reversable(payment)
        reversal = payment.reversed_payment or ReversedPayment(
            reference_code=generate_payment_reference(),
            payment_code=payment.Reference,
            payment=payment
        )
        cls.reverse_reversal(reversal, user)

    @classmethod
    def mark_as_handled(cls, reversal, user):
        if reversal.handled:
            raise Error('The reversal request has already been handled')
        reversal.handled = True
        reversal.user = user
        reversal.reversed_on = datetime.now()

    @classmethod
    def reverse_reversal(cls, reversal, user=None):
        if reversal.reconciled_payment:
            raise Error('The reversal request has already been reversed.')
        if not reversal.payment:
            raise Error('The reversal request has no payment and cannot be reversed.')
        cls._check_reversable(reversal.payment)

        if reversal.payment.used:
            if not user and not SettingsService.get_setting('AutomaticRepaymentReversal'):
                raise Error('The payment cannot be automatically reversed.')

            # We need a separate check as the if there is a lead downpayment the refund function will cancel all
            # We also check if the lead is not already installed
            lead_reconciliation = reversal.payment.reconciled_payments.filter(lambda r: r.lead is not None).first()
            if lead_reconciliation and not lead_reconciliation.lead.contract:
                EditLeadService.refund_deposit(lead_reconciliation.lead)
            
            for reconciled in reversal.payment.reconciled_payments:
                if reconciled.repayment and not reconciled.repayment.converse:
                    ReverseRepaymentService.create(
                        user=user,
                        uuid=str(uuid1()),
                        repayment_id=reconciled.repayment.id
                    )
                elif not reconciled.converse:
                    ReconciledPaymentService.revert(reconciled)
        if reversal.payment.back_payment:
            back_payment = Payment.get(id=reversal.payment.back_payment.id)
            ReconciledPayment(
                time=datetime.now(),
                amount=reversal.payment.Amount,
                payment_account=back_payment.PaymentWallet,
                type=ReconciledPaymentType.payment_reversal
            )
            back_payment.processed = True
        if reversal.payment.PaymentWallet.balance < reversal.payment.Amount:
            raise Error('The money was already used in a way that cannot be reversed. ')
        cls.mark_as_handled(reversal, user)
        ReconciledPayment(
            time=datetime.now(),
            amount=reversal.payment.Amount,
            payment_account=reversal.payment.PaymentWallet,
            type=ReconciledPaymentType.payment_reversal,
            reversed_payment=reversal
        )
        reversal.payment.processed = True

    @staticmethod
    def _check_reversable(payment):
        if not payment.reversable:
            raise Error('The payment cannot be reversed since the money has been used.')
