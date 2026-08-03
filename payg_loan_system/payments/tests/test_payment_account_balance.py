from datetime import datetime
import pytest
from pony import orm
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.payments.models.wallet import PaymentWallet
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.contracts.models.reconciled_payment_model import ReconciledPayment


class TestPaymentAccountBalanceCalculator:

    @orm.db_session
    def test_zero_balance_at_account_creation(self, *args):
        account = PaymentWallet(
            RegistrationDate=datetime.now(),
            FullName='TEST 1',
            operator=''
        )
        assert account.get_balance() == 0

    @orm.db_session
    def test_positive_balance_with_repayment(self, *args):
        account = PaymentWallet(
            RegistrationDate=datetime.now(),
            FullName='TEST 2',
            operator=''
        )
        payment = Payment(
            Amount=1000,
            Reference='TEST2A',
            PaymentTime=datetime.now(),
            PaymentReceptionTime=datetime.now(),
            PaymentWallet=account
        )
        orm.flush()
        assert account.get_balance() == 1000

    @orm.db_session
    def test_positive_balance_with_repayment_and_reconciliation(self, *args):
        account = PaymentWallet(
            RegistrationDate=datetime.now(),
            FullName='TEST 3',
            operator=''
        )
        payment = Payment(
            Amount=1000,
            Reference='TEST3A',
            PaymentTime=datetime.now(),
            PaymentReceptionTime=datetime.now(),
            PaymentWallet=account
        )
        reconciled_payment = ReconciledPayment(
            time=datetime.now(),
            amount=500,
            type=ReconciledPaymentType.manual_adjustment,
            payment_account=account
        )
        orm.flush()
        assert account.get_balance() == 500

        reconciled_payment = ReconciledPayment(
            time=datetime.now(),
            amount=1000,
            type=ReconciledPaymentType.manual_adjustment,
            payment_account=account
        )
        with pytest.raises(Exception) as error:
            orm.commit()
        assert str(error.value) == f"There is not sufficient balance ({account.get_balance()}) to use that amount (1000). "
