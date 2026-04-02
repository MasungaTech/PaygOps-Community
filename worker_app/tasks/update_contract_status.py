from datetime import datetime, timedelta
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.models.contract_status import ContractStatus
from shared.services.settings_service import SettingsService
from worker_app.worker_app import worker_app
from pony.orm import db_session

from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.models.contract_status import ContractStatus
from shared.services.settings_service import SettingsService
from worker_app.worker_app import worker_app
from pony.orm import db_session

@worker_app.task
@db_session
def update_contract_status():
    enable_late_status = SettingsService.get_setting('EnableLateStatus')
    days_late_for_late_status = SettingsService.get_setting('DaysLateForLateStatus')
    print(f'Updating contracts with more than {days_late_for_late_status} days late to late status')
    if enable_late_status:
        contracts = Contract.select(lambda c: c.status == ContractStatus.active and c.next_repayment_due_time <= (datetime.now() - timedelta(days=days_late_for_late_status)))
        for contract in contracts:
            contract.status = ContractStatus.late
        late_contracts_that_should_be_active = Contract.select(lambda c: c.status == ContractStatus.late and c.next_repayment_due_time > (datetime.now() - timedelta(days=days_late_for_late_status)))
        for contract in late_contracts_that_should_be_active:
            contract.status = ContractStatus.active
    else:
        # We put back all contracts to active if the late status is not enabled
        late_contracts = Contract.select(lambda c: c.status == ContractStatus.late)
        for contract in late_contracts:
            contract.status = ContractStatus.active
