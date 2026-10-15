from pony.orm import db_session, flush
from tests.base_test import BaseViewTest, BaseTestMethods
from tests.factories.factories import PaymentWalletFactory, PaymentFactory, ClientFactory, PersonFactory, ReversedPaymentFactory
from payg_loan_system.payments.models.wallet import PaymentWalletType


class TestListReversedPayments(BaseViewTest):
    url = 'reversed_payment.list_all'
    template = 'list_reversed_payments.html'


class TestUnhandledReversePaymentList(BaseViewTest):
    url = 'reversed_payment.list_all'
    template = 'list_reversed_payments.html'
    params = dict(status='unhandled')


class TestHandledReversePaymentList(BaseViewTest):
    url = 'reversed_payment.list_all'
    template = 'list_reversed_payments.html'
    params = dict(path='handled')


class TestViewReversedPayment(BaseViewTest):

    reversed_payment_id = 1
    url = 'reversed_payment.view_reversal'
    template = 'view_reversed_payment.html'
    params = dict(reversal_id=reversed_payment_id)

    @classmethod
    @db_session
    def setup_class(cls):
        revered_payment = ReversedPaymentFactory()
        payment = PaymentFactory(
            reversed_payment=revered_payment,
            PaymentWallet=PaymentWalletFactory(
                Type=PaymentWalletType.mobile_money,
                client=ClientFactory(person=PersonFactory())
            )
        )
        flush()
        cls.reversed_payment_id = revered_payment.id
        cls.params = dict(reversal_id=cls.reversed_payment_id)

    @db_session
    def test_invalid_id_returns_404(self, super_admin_app):
        self.params = dict(reversal_id=100)
        res = self.get(super_admin_app)
        assert res.status_code == 404


class TestMarkAsHandled(BaseTestMethods):

    reversed_payment_id = 1
    url = 'reversed_payment.mark_handled'
    template = 'list_reversed_payments.html'
    params = dict(reversal_id=1)

    @classmethod
    @db_session
    def setup_class(cls):
        revered_payment = ReversedPaymentFactory()
        payment = PaymentFactory(
            reversed_payment=revered_payment,
            PaymentWallet=PaymentWalletFactory(
                Type=PaymentWalletType.mobile_money,
                client=ClientFactory(person=PersonFactory())
            )
        )
        flush()
        cls.reversed_payment_id = revered_payment.id
        cls.params = dict(reversal_id=cls.reversed_payment_id)

    @db_session
    def test_flashes_when_success(self, super_admin_app):
        res = self.post(super_admin_app, self.params)
        assert b'Marked reversal with id: ' in res.data


