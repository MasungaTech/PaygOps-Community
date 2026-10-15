from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.contract_model import Contract
from pony import orm
from payg_loan_system.contracts.models.repayment_model import ContractRepayment


class ContractListService:

    @classmethod
    def get_from_clients(cls, clients):
        return orm.select(contract for contract in Contract if contract.client in clients)

    @classmethod
    def get_from_clients_ids(cls, clients_ids):
        return orm.select(contract for contract in Contract if contract.client.id in clients_ids)

    @classmethod
    def filter_only_active(cls, contract_list):
        return contract_list.filter(lambda contract: contract.status == ContractStatus.active)
    
    @classmethod
    def filter_active_or_late(cls, contract_list):
        return contract_list.filter(lambda contract: contract.status in [ContractStatus.active, ContractStatus.late])
    
    @classmethod
    def filter_by_payment_due_after(cls, contract_list, target_due_time):
        contract_list = cls.filter_active_or_late(contract_list)
        return contract_list.filter(lambda contract: contract.next_repayment_due_time > target_due_time)

    @classmethod
    def filter_by_payment_due_before(cls, contract_list, target_due_time):
        contract_list = cls.filter_active_or_late(contract_list)
        return contract_list.filter(lambda contract: contract.next_repayment_due_time < target_due_time)

    @classmethod
    def filter_by_repayment_after_date(cls, contract_list, limit_date):
        repayments = orm.select(repayment for repayment in ContractRepayment if repayment.time >= limit_date)
        repayment_contracts = orm.select(repayment.contract for repayment in repayments)
        return contract_list.filter(lambda contract: contract in repayment_contracts)
