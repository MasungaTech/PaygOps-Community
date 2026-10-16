
from datetime import datetime, timedelta

from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.models.reconciled_payment_model import ReconciledPayment
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.services.payment_processor_service import PaymentProcessorService
from payg_loan_system.payments.services.payment_router_service import PaymentRouterService
from shared.helpers.chunk_executer import isolated_chunk_executer
from shared.services.settings_service import SettingsService
from worker_app.worker_app import worker_app
from pony.orm import db_session, commit, select, rollback
from shared.logger.loggers import LogAPI
from core_system.core_entities import db

# A payment row is committed before routing finishes. Leave payments received
# inside this window for the next run so this task does not route them while
# the original request is still sending the payment-received SMS.
RECENT_PAYMENT_GRACE_PERIOD = timedelta(minutes=5)


@worker_app.task
def fix_payment_processing(*args, **kwargs):


    with db_session:
        print('Checking payments with outdated orphaned info...')
        payments_query = db.execute('''
            SELECT p.id, p.reference
            FROM "payment" p
            LEFT JOIN (
                SELECT "mpesa_account", COALESCE(SUM("amount"), 0) AS total_received
                FROM "payment"
                GROUP BY "mpesa_account"
            ) p2 ON p."mpesa_account" = p2."mpesa_account"
            LEFT JOIN (
                SELECT "payment_account", COALESCE(SUM("amount"), 0) AS total_reconciled
                FROM "reconciledpayment"
                GROUP BY "payment_account"
            ) r ON p."mpesa_account" = r."payment_account"
            LEFT JOIN (
                SELECT "linked_payment", COALESCE(SUM("amount"), 0) AS total_used
                FROM "reconciledpayment"
                GROUP BY "linked_payment"
            ) r2 ON p."id" = r2."linked_payment"
            WHERE (
                (p2.total_received <> r.total_reconciled AND not "p"."cached_remaining_positive" AND total_used <> p.amount)
                OR ((p2.total_received = r.total_reconciled OR total_used = p.amount) AND "p"."cached_remaining_positive")
            )
        ''')
        payments = payments_query.fetchall()
        if payments:
            LogAPI.Warning(f'Updating [{len(payments)}] cached orphaned info', other_data=[p[1] for p in payments])
            isolated_chunk_executer(
                [p[0] for p in payments],
                Payment,
                lambda p: p.payment_or_reconciled_changed(),
                action_name='Update orphaned payment info',
            )

    with db_session:
        print('Checking reconciled payment without destination...')
        reconciled_payments = ReconciledPayment.select(lambda rp: rp.type != ReconciledPaymentType.manual_adjustment and not (
            rp.repayment or
            rp.lead or
            rp.add_on or
            rp.contract_pending_repayment or
            rp.user or
            rp.person or 
            rp.reversed_payment
        ))
        print(f'Removing {reconciled_payments.count()} reconciled payments without valid destination')
        payments = []
        for rp in reconciled_payments:
            if rp.linked_payment:
                payments.append(rp.linked_payment)
            rp.delete()
        commit()
        for payment in payments:
            try:
                payment.payment_or_reconciled_changed()
                commit()
            except Exception as e:
                LogAPI.FatalNoRequest(e)
        
    
    with db_session:
        grace_cutoff = datetime.now() - RECENT_PAYMENT_GRACE_PERIOD
        unprocessed_payments = Payment.select(lambda p: not p.processed and p.PaymentReceptionTime <= grace_cutoff)
        recent_unprocessed_count = Payment.select(lambda p: not p.processed and p.PaymentReceptionTime > grace_cutoff).count()
        print(f"Fixing {unprocessed_payments.count()} unprocessed payments...")
        if recent_unprocessed_count:
            print(f"Skipping {recent_unprocessed_count} unprocessed payments received in the last {int(RECENT_PAYMENT_GRACE_PERIOD.total_seconds() // 60)} minutes.")
        for payment in unprocessed_payments:
            try:
                if payment.back_payment:
                    if payment.back_payment.processed:
                        payment.processed = True
                        continue
                    if payment.PaymentWallet.client:
                        PaymentProcessorService.process_payment_for_target(
                            payment,
                            payment.PaymentWallet.client.active_contract,
                            reprocessing=False,
                            error_handler=None
                        )
                else:
                    PaymentRouterService.route_payment(payment, error_handler=lambda e: [])
                commit()
            except Exception as e:
                if str(e) == 'PAYMENT_ALREADY_USED':
                    # It was processed by something else in between
                    payment.processed = True
                    commit()
                else:
                    LogAPI.FatalNoRequest(e)

    with db_session:
        types_to_activate = [k for k,v in SettingsService.get_setting('AllDeviceAPIS').items() if v['device_api_type'] != "TWO_WAY_CODE"]
        unprocessed_repayments = ContractRepayment.select(lambda r:  r.time > r.contract.linked_device.RegistrationTime and r.contract.linked_device.type in types_to_activate and not r.token and not r.processed)
        contracts_with_unprocessed_repayments = select(r.contract for r in unprocessed_repayments)
        contracts_with_unprocessed_repayments_count = contracts_with_unprocessed_repayments.count()
        print(f"Fixing {unprocessed_repayments.count()} unprocessed repayments of {contracts_with_unprocessed_repayments_count} contracts...")
        processed = 0
        for contract in contracts_with_unprocessed_repayments:
            contract = Contract.get(id=contract.id) # needed cause we are handling exceptions to avoid db_session ended errors
            try:
                ContractRepaymentService.process_contract_with_unprocessed_repayments(contract)
            except Exception as e:
                rollback()
                LogAPI.FatalNoRequest(e)
            processed += 1
            if (processed % 10) == 0 or processed >= contracts_with_unprocessed_repayments_count:
                print(f'Processed {processed} out of {contracts_with_unprocessed_repayments_count} contracts.')