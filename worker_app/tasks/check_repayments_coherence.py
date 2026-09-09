from worker_app.worker_app import worker_app
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.repayment_model import ContractRepayment, ContractRepaymentDiscountTypes
from pony.orm import db_session, desc
from shared.logger.loggers import LogAPI

log_api = LogAPI()


@worker_app.task
@db_session
def check_repayments_coherence():
    print('Checking repayments coherence...')
    repayments = ContractRepayment.select(lambda r: (
        r.discount_type not in [ContractRepaymentDiscountTypes.reversal, ContractRepaymentDiscountTypes.downpayment_reversal] and
        not r.converse and
        r.total_reconciled != r.amount_paid
    ))
    result_dict = {}
    for repayment in repayments:
        last_one = repayment.contract.repayments.select().order_by(desc(ContractRepayment.time)).first() == repayment
        completed = repayment.contract.status == ContractStatus.completed
        more_reconciled_than_paid = repayment.total_reconciled > repayment.amount_paid
        if last_one and completed and more_reconciled_than_paid:
            last_reconciled = repayment.reconciled_payments.select().order_by(lambda r: desc(r.time)).first()
            last_reconciled.amount -= repayment.total_reconciled-repayment.amount_paid
            continue
        result_dict[repayment.contract.reference] = result_dict.get(repayment.contract.reference, [])
        result_dict[repayment.contract.reference].append({
            'paid': str(repayment.amount_paid),
            'reconciled': str(repayment.total_reconciled),
            'id': repayment.id
        })
    if result_dict:
        log_api.FatalNoRequest(Exception(
            'Repayment mismatching', result_dict
        ))
    print('Checked repayments coherence...')
