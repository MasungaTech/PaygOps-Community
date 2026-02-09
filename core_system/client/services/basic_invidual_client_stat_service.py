from payg_loan_system.contracts.models.contract_status import ContractStatus
from pony.orm.core import select


class IndividualClientStatService:

    @classmethod
    def get_earliest_payment_due(cls, client):
        return select(c.next_repayment_due_time for c in client.contracts.select(
            lambda c: c.status in [ContractStatus.active, ContractStatus.late]
        )).min()

    @classmethod
    def get_average_repayment_progression(cls, client, cached=False):
        progression_sum = 0
        count = 0
        for contract in client.contracts:
            progression = contract.cached_percentage_paid/100 if (cached and contract.cached_percentage_paid is not None) else contract.get_percentage_repaid()
            if not progression:
                return None
            progression_sum += progression
            count += 1
        if count > 0:
            return progression_sum / count
        return 0

    @classmethod
    def get_average_timeliness_ratio(cls, client, cached=False):
        timeliness_sum = 0
        count = client.contracts.count()
        if count != 0:
            for contract in client.contracts:
                timeliness = contract.cached_timeliness_ratio if (cached and contract.cached_timeliness_ratio is not None) else contract.get_timeliness_ratio()
                if timeliness:
                    timeliness_sum += timeliness
            timeliness_sum = timeliness_sum / count
        return timeliness_sum

    @classmethod
    def get_overall_status(cls, client):
        status = None
        for contract in client.contracts:
            if contract.status == ContractStatus.active:
                return ContractStatus.active
            elif contract.status == ContractStatus.paused:
                status = ContractStatus.paused
            elif contract.status == ContractStatus.overpaid:
                status = ContractStatus.overpaid
            elif contract.status == ContractStatus.completed:
                status = ContractStatus.completed
            elif contract.status == ContractStatus.defaulted:
                # We do that because if they have a completed contract it matters more
                if status != ContractStatus.completed:
                    status = ContractStatus.defaulted
            elif contract.status == ContractStatus.cancelled:
                # We do that because if they have a completed contract it matters more
                if status != ContractStatus.completed:
                    status = ContractStatus.cancelled
            elif contract.status == ContractStatus.late:
                if status != ContractStatus.completed:
                    status = ContractStatus.late
        return status
