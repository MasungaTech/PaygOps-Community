from pony.orm import db_session, desc

from tests.factories.factories import PaymentWalletFactory
from payg_loan_system.payments.services.payment_creation_service import PaymentCreationService


class TestPaymentCreationService:

    @db_session
    def test_create_paying_account_returns_paying_account(self):
        paying_account = PaymentCreationService._create_payment_wallet('gerard butler')
        assert paying_account.FullName == 'gerard butler'

        paying_account.delete()

    @db_session
    def test_get_paying_account(self):
        full_name = 'jimmy three fingers'
        existing_account = PaymentWalletFactory(FullName=full_name)

        paying_account = PaymentCreationService._get_or_create_payment_wallet(full_name)

        assert existing_account.FullName == paying_account.FullName
        paying_account.delete()

    @db_session
    def test_get_paying_account_automatic_creation(self):
        full_name = 'jimmy twenty fingers'
        paying_account = PaymentCreationService._get_or_create_payment_wallet(full_name)

        assert paying_account.get_balance() == 0
        paying_account.delete()


