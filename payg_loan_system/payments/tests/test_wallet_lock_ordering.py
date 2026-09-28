from datetime import datetime
from pony import orm
from payg_loan_system.payments.models.wallet import PaymentWallet
from payg_loan_system.payments.services.payment_router_service import PaymentRouterService


class TestWalletLockOrdering:

    def _create_wallet(self, name):
        with orm.db_session:
            wallet = PaymentWallet(RegistrationDate=datetime.now(), FullName=name, operator='')
            orm.flush()
            return wallet.id

    def test_lock_row_returns_the_wallet(self, *args):
        wallet_id = self._create_wallet('TEST LOCK 1')
        with orm.db_session:
            locked = PaymentWallet.lock_row(wallet_id)
            assert locked.id == wallet_id

    def test_lock_row_tolerates_missing_wallet(self, *args):
        with orm.db_session:
            assert PaymentWallet.lock_row(999999) is None

    def test_route_payment_locks_wallet_before_processing(self, *args):
        wallet_id = self._create_wallet('TEST LOCK 2')
        calls = []
        original = PaymentWallet.lock_row.__func__

        def spy(cls, wid):
            calls.append(wid)
            return original(cls, wid)

        PaymentWallet.lock_row = classmethod(spy)
        try:
            with orm.db_session:
                from payg_loan_system.payments.models.payment import Payment
                payment = Payment(
                    Amount=1000, Reference='TEST LOCK 2-P1',
                    PaymentTime=datetime.now(), PaymentReceptionTime=datetime.now(),
                    PaymentWallet=PaymentWallet[wallet_id]
                )
                orm.flush()
                PaymentRouterService.route_payment(payment, reprocessing=True, error_handler=lambda e: [])
            assert wallet_id in calls
        finally:
            PaymentWallet.lock_row = classmethod(original)
