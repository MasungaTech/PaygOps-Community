from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWalletType
from payg_loan_system.payments.services.payment_router_service import PaymentRouterService
from pony import orm
from shared.logger.loggers import LogAPI

log_api = LogAPI()


class OrphanedPaymentService:

    @classmethod
    @orm.db_session
    def _process_payment(cls, payment_id):
        payment = Payment.get(id=payment_id)
        if payment.orphaned_cached and payment.PaymentWallet.cached_balance_positive:
            PaymentRouterService.route_payment(payment, reprocessing=True, error_handler=lambda e: [])
        orm.commit()

    @classmethod
    def auto_route_orphaned_payments(cls, from_date=None, to_date=None, exclude_reverted=True):
        with orm.db_session:
            orphaned_payments = cls.get_orphaned_payments(from_date, to_date, exclude_reverted=exclude_reverted)
            count = orphaned_payments.count()
            ids = [p.id for p in orphaned_payments]
        print(f'Found {count} orphaned payments')
        for payment_id in ids:
            try: cls._process_payment(payment_id)
            except orm.IsolationError as e:
                try: cls._process_payment(payment_id)
                except orm.IsolationError as e: pass
                except Exception as e:
                    log_api.FatalNoRequest(e)
            except Exception as e:
                log_api.FatalNoRequest(e)
        return count

    @classmethod
    def get_orphaned_payments(cls, from_date=None, to_date=None, exclude_reverted=False, cached=True):
        if cached:
            orphaned_payments = Payment.select(
                lambda p: p.PaymentWallet.Type != PaymentWalletType.agent_collection
                and p.orphaned_cached and p.PaymentWallet.cached_balance_positive
            )
        else:
            orphaned_payments = Payment.select(
                lambda p: p.PaymentWallet.Type != PaymentWalletType.agent_collection
                and p.orphaned and p.PaymentWallet.balance
            )
        if from_date:
            orphaned_payments = orphaned_payments.filter(lambda p: p.PaymentReceptionTime >= from_date)
        if to_date:
            orphaned_payments = orphaned_payments.filter(lambda p: p.PaymentReceptionTime < to_date)
        if exclude_reverted:
            orphaned_payments = orphaned_payments.filter(lambda p: not p.reconciled_payments.filter(lambda r: r.converse))
        return orphaned_payments
