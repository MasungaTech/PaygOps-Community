from payg_loan_system.payments.models.payment import Payment
from pony import orm
from worker_app.worker_app import worker_app


@worker_app.task
@orm.db_session(sql_debug=False)
def migrate_payments_wrongly_marked_as_not_orphaned():
    print('Migrating payments with orphaned cached == True')
    Payment.check_data_coherence = lambda p: None # We remove integrity check
    payments = Payment.select(lambda p: not p.orphaned_cached)
    for payment in payments:
        if payment.orphaned:
            payment.payment_or_reconciled_changed()