from payg_loan_system.contracts.models.contract_model import Contract
from pony import orm
from worker_app.worker_app import worker_app


@worker_app.task
@orm.db_session(sql_debug=False)
def migrate_repayments_wrong_time():
    contracts = Contract.select()
    for contract in contracts:
        last = contract.start_time
        for repayment in contract.repayments.order_by(lambda r: r.id):
            if repayment.time < last:
                repayment.time = last
            last = repayment.time