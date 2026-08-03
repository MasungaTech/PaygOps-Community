from datetime import datetime
from decimal import Decimal

from pony import orm

from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWallet
from payg_loan_system.payments.services.payment_creation_service import PaymentCreationService
from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.edit_lead_service import EditLeadService
from shared.helpers.client_creator import ClientCreator


class TestReconciliationService:

    @orm.db_session
    def test_create_reconciliation_does_not_replace_explicit_zero_amount_with_payment_remaining(self):
        account = PaymentWallet(
            RegistrationDate=datetime.now(),
            FullName='PARTIAL_REC_ZERO_AMOUNT',
            operator=''
        )
        payment = Payment(
            Amount=200,
            Reference='PARTIAL_REC_ZERO_AMOUNT',
            PaymentTime=datetime.now(),
            PaymentReceptionTime=datetime.now(),
            PaymentWallet=account
        )
        orm.flush()

        assert ReconciledPaymentService.create_reconciliation(
            payment=payment,
            account=account,
            amount=0,
            type=ReconciledPaymentType.manual_adjustment,
            note='zero adjustment'
        ).amount == 0

    @orm.db_session
    def test_partial_lead_reconciliation_only_uses_requested_amount(self):
        user = UserGetterService.get_by_username("super_admin@test.com")
        lead = ClientCreator.create_lead(offer_data={
            'code': 'PARTIAL_LEAD_REC_OFFER',
            'name': 'Partial Lead Rec Offer',
            'type': 'Loan',
            'downpayment': 200,
            'registration_fee': 200,
            'time_to_ownership_in_days': 365,
            'time_given_at_start_in_days': 0,
            'base_price_amount': 1000,
            'raw_unit_cost': '',
            'family': 'Home',
            'base_price_time_in_days': 1,
            'automatic_unlock_code_sending': 'True',
            'in_use_for_new_leads': 'True',
            'can_be_approved_and_registered': 'True'
        })
        EditLeadService.edit_lead(lead, {
            'status': LeadStatus.get_first(StatusCategory.awaiting_payment).id,
            'offer_editing_locked': True,
        }, user)
        orm.flush()

        reference = f'test_partial_rec_lead{lead.id}'
        payment = PaymentCreationService.create_payment(
            reference,
            200,
            datetime.now(),
            f'UNROUTED_PARTIAL_REC_{lead.id}',
            phone_number=f'+23499{lead.id:07d}',
        )
        assert payment.remaining == 200

        ReconciliationService.get_answer_for_lead(lead, payment, amount=Decimal('100'), user=user)
        orm.flush()

        assert payment.total_reconciled == 100
        assert payment.remaining == 100
        assert lead.already_paid == 100
