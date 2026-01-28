from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWallet
from pony import orm
from datetime import datetime


@orm.db_session
def create_payments():
    new_account = PaymentWallet(
        RegistrationDate=datetime.now(),
        FullName='TEST_PAYMENT_ACCOUNT',
        operator=''
    )

    amount_1 = 50000
    this_payment = Payment(
        Amount=amount_1,
        Reference='TEST_PAYMENT_REFERENCE_1',
        PaymentTime=datetime.now(),
        PaymentReceptionTime=datetime.now(),
        PaymentWallet=new_account
    )

    new_account_2 = PaymentWallet(
        RegistrationDate=datetime.now(),
        FullName='TEST_PAYMENT_ACCOUNT_2',
        operator=''
    )

    amount_2 = 100000
    this_payment_2 = Payment(
        Amount=amount_2,
        Reference='TEST_PAYMENT_REFERENCE_2',
        PaymentTime=datetime.now(),
        PaymentReceptionTime=datetime.now(),
        PaymentWallet=new_account_2
    )
