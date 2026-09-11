from datetime import datetime, timedelta
from pony.orm import db_session, select
from payg_loan_system.payments.services.orphaned_payment_service import OrphanedPaymentService
from shared.services.settings_service import SettingsService
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.services.contract_cache_service import ContractCacheService
from worker_app.worker_app import worker_app
from shared.logger.loggers import LogService


@worker_app.task
def autoreconciliate(*args, **kwargs):
    # We autofix orphaned repayments
    reasons_dict = {}
    with db_session:
        now = datetime.now()
        since = now - timedelta(hours=3)
        invalid_repayments = select(r for r in ContractRepayment if r.time > since and r.orphaned_simple_payment)
        invalid_repayments_count = invalid_repayments.count()
        if invalid_repayments_count > 0:
            for rp in invalid_repayments:
                reason = ContractCacheService.fix_orphaned_repayment(rp)
                if not reason in reasons_dict:
                    reasons_dict[reason] = []
                else:
                    reasons_dict[reason].append(rp.contract.reference)
            LogService.Warning(f'Found [{invalid_repayments_count}] simple repayments without reconciled payment.', other_data={
                'invalid_repayments': [(p.id, p.contract.reference) for p in invalid_repayments],
                'fix_details': reasons_dict
            })
    
    with db_session:
        enabled = SettingsService.get_setting('AutomaticAutoReconcile')
    if enabled:
        now = datetime.now()
        since = now - timedelta(hours=24)
        OrphanedPaymentService.auto_route_orphaned_payments(since, now)


@worker_app.task
def autoreconciliate_week(*args, **kwargs):
    with db_session:
        enabled = SettingsService.get_setting('AutomaticAutoReconcileWeek')
    if enabled:
        now = datetime.now()
        since = now - timedelta(hours=24*7)
        OrphanedPaymentService.auto_route_orphaned_payments(since, now)