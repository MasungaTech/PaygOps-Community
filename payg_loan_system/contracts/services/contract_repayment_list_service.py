from pony import orm
from pony.orm import desc
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from shared.helpers.form_helpers import value_to_bool

from shared.services.base_getter_service import BaseGetterService


class ContractRepaymentListService(BaseGetterService):

    OBJ_NAME = 'Contract Repayment'

    @classmethod
    def get_filtered_objects(cls, current_user, client_id=None, contract_reference='', repayment_type='', from_date=None, to_date=None, include_reversed=None, reverse_order=False, **kwargs):
        contracts = ContractGetterService.get_list(current_user)
        list_objects = orm.select(r for r in ContractRepayment if r.contract in contracts)
        # We filter
        if client_id:
            list_objects = list_objects.filter(lambda o: o.contract.client.id == client_id)
        if contract_reference:
            list_objects = list_objects.filter(lambda o: o.contract.reference == contract_reference)
        if repayment_type:
            if repayment_type == 'Contract Payment': repayment_type = ''
            list_objects = list_objects.filter(lambda o: o.discount_type == repayment_type)
        if from_date:
            list_objects = list_objects.filter(lambda o: o.time >= from_date)
        if to_date:
            list_objects = list_objects.filter(lambda o: o.time < to_date)
        if include_reversed is not None:
            list_objects = list_objects.filter(lambda o: bool(o.converse) == include_reversed)
        if value_to_bool(reverse_order):
            return list_objects.order_by(lambda r: desc(r.time))
        return list_objects.order_by(lambda r: r.time)
