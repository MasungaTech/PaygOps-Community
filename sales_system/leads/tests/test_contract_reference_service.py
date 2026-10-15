from payg_loan_system.contracts.services.contract_reference_service import ContractReferenceService
from mock import Mock


class TestContractReferenceService:

    def test_luhn_key_generator(self):
        number_1 = 453201511283036
        key_1 = 6
        assert ContractReferenceService._get_luhn_check_digit_of_number(number_1) == key_1
        number_2 = 601151443354620
        key_2 = 1
        assert ContractReferenceService._get_luhn_check_digit_of_number(number_2) == key_2
        number_3 = 677154949558680
        key_3 = 2
        assert ContractReferenceService._get_luhn_check_digit_of_number(number_3) == key_3

    def test_generate_contract_reference(self):
        example_contract_reference = 'C88880224'
        person = Mock(id=8888)
        next_internal_number = 22
        contract_reference = ContractReferenceService._generate_contract_reference(person, next_internal_number)
        assert contract_reference == example_contract_reference
