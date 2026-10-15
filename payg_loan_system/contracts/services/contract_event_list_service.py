from pony import orm
from payg_loan_system.contracts.models.contract_event_model import ContractEvent
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
import dateutil.parser
from datetime import datetime

from shared.services.base_getter_service import BaseGetterService


class ContractEventListService(BaseGetterService):

    OBJ_NAME = 'Contract Event'

    @classmethod
    def get_filtered_objects(cls, current_user, client_id=None, contract_reference='', event_type='', from_date=None, to_date=None, **kwargs):
        contracts = ContractGetterService.get_list(current_user)
        list_objects = orm.select(r for r in ContractEvent if r.contract in contracts)
        # We filter
        if client_id:
            list_objects = list_objects.filter(lambda o: o.contract.client.id == client_id)
        if contract_reference:
            list_objects = list_objects.filter(lambda o: o.contract.reference == contract_reference)
        if event_type:
            list_objects = list_objects.filter(lambda o: o.type == event_type)
        if from_date:
            list_objects = list_objects.filter(lambda o: o.time >= from_date)
        if to_date:
            list_objects = list_objects.filter(lambda o: o.time < to_date)
        return list_objects
