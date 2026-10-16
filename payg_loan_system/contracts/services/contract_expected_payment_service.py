

from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService

from shared.logger.loggers import Error

class ExpectedPaymentService:
    @classmethod
    def get_from_user_and_properties(cls, user, **kwargs):
        contract = ContractGetterService.get_from_user_and_properties(user, reference=kwargs['reference'], strict=True, main_resource=True)
        return ExpectedPaymentsObj(contract)

    @classmethod
    def get_affected_entity(cls, data, user, **kwargs):
        reference = kwargs.get('id')
        if not reference:
            raise Error('Reference not found')
        contract =  ContractGetterService.get_from_user_and_properties(user, reference=reference)
        if not contract:
            raise Error('Contract not found')
        return contract.client.person.village


class ExpectedPaymentsObj:
    def __init__(self, contract):
        self.contract = contract
    
    def get_serialized_object(self, **kwargs):
        return self.preprocess_data(self.contract.get_expected_payments_table(cached=True, parsed=True))
    
    def preprocess_data(self, data):
        return [{'date': ep[0], 'amount': ep[1], 'total_expected_paid':ep[2], 'type':ep[3]} for ep in data]