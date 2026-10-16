from datetime import datetime, timedelta
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.services.contract_list_service import ContractListService


class ContractStatsService:

    @classmethod
    def get_number_of_non_defaulted_contracts_in_period(cls, contracts, from_time, to_time):
        contracts = contracts.filter(
            lambda contract: contract.start_time <= to_time
                             and (not contract.end_time
                                  or contract.end_time > to_time
                                  or contract.status == ContractStatus.completed)
        )
        return contracts.count()

    @classmethod
    def get_number_of_active_contracts_in_period(cls, contracts, from_time, to_time):
        contracts = contracts.filter(
            lambda contract: contract.start_time <= to_time
                             and (not contract.end_time
                                  or contract.end_time > to_time)
        )
        return contracts.count()

    @classmethod
    def get_number_of_defaulted_contract_in_period(cls, contracts, from_time, to_time):
        contracts = contracts.filter(
            lambda contract: contract.end_time >= from_time
                             and contract.end_time < to_time
                             and contract.status == ContractStatus.defaulted
        )
        return contracts.count()

    @classmethod
    def get_number_of_new_contracts_in_period(cls, contracts, from_time, to_time):
        contracts = contracts.filter(
            lambda contract: contract.start_time >= from_time
                             and contract.start_time < to_time
        )
        return contracts.count()

    @classmethod
    def get_default_rate_in_period(cls, contracts, from_time, to_time):
        active_contracts = cls.get_number_of_active_contracts_in_period(contracts, from_time,  to_time)
        defaulted_contracts = cls.get_number_of_defaulted_contract_in_period(contracts, from_time, to_time)
        if active_contracts:
            return (defaulted_contracts/active_contracts)*100
        else:
            return 0

    @classmethod
    def get_par_data(cls, contracts):
        target_active = datetime.now()
        target_par7 = datetime.now() - timedelta(days=7, hours=-12)  # 12 hours for rounding
        target_par30 = datetime.now() - timedelta(days=30, hours=-12)  # 12 hours for rounding
        target_par90 = datetime.now() - timedelta(days=90, hours=-12)  # 12 hours for rounding

        total = ContractListService.filter_active_or_late(contracts).count()
        active_count = ContractListService.filter_by_payment_due_after(contracts, target_active).count()
        par7_count = ContractListService.filter_by_payment_due_after(contracts, target_par7).count()
        par30_count = ContractListService.filter_by_payment_due_after(contracts, target_par30).count()
        par90_count = ContractListService.filter_by_payment_due_after(contracts, target_par90).count()

        active = active_count
        par7 = par7_count - active_count
        par30 = par30_count - par7_count
        par90 = par90_count - par30_count
        par90plus = total - par90_count

        par_dict = {
            'active': active,
            'par': par7,
            'par7': par30,
            'par30': par90,
            'par90': par90plus,
            'total': total
        }
        return par_dict

