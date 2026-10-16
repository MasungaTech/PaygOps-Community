from shared.helpers.db_helpers import TypeClassBase


class ContractStatus(TypeClassBase):
    completed = 'Completed'
    defaulted = 'Defaulted'
    active = 'Active'
    cancelled = 'Cancelled'
    paused = 'Paused'
    overpaid = 'Overpaid'
    late = 'Late'


INACTIVE_CONTRACT_STATUS = [
    ContractStatus.cancelled, 
    ContractStatus.completed, 
    ContractStatus.defaulted
]
