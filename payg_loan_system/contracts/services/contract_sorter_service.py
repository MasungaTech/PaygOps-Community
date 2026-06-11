from payg_loan_system.contracts.models.contract_model import Contract
from shared.services.sorter import Sorter
from pony import orm


class ContractSorter(Sorter):

    def sort_by(field_name):
        options = {}
        return options.get(field_name, Contract.id)
    
    def real_field_sort(field_name, desc=False):
        options = {
            'id': Contract.id,
            'client_name': lambda C: C.client.full_name,
            'offer_code': lambda C: C.offer.code,
            'type': lambda C: C.offer.type,
            'status': Contract.status,
            'next_payment_due': Contract.next_repayment_due_time,
            'progress': Contract.cached_percentage_paid,
            'timeliness': Contract.cached_timeliness_ratio,
            'days_late': Contract.cached_cumulative_days_late
        }
        options_desc = {
            'client_name': lambda C: orm.desc(C.client.full_name),
            'offer_code': lambda C: orm.desc(C.offer.code),
            'type': lambda C: orm.desc(C.offer.type),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, Contract.id))
        return options.get(field_name, Contract.id)
