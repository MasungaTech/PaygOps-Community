from pony import orm
from core_system.core_entities import db


class ContractReferenceService:

    @classmethod
    def generate_for_lead(cls, lead, initial_migration=False):
        return cls.generate_for_person(lead.person, initial_migration)

    @classmethod
    def generate_for_person(cls, person, initial_migration=False):
        last_internal_number = cls._get_last_contract_number_for_person(person, initial_migration)
        next_internal_number = last_internal_number + 1
        new_contract_reference = cls._generate_contract_reference(person, next_internal_number)
        while cls._contract_reference_exists(new_contract_reference, initial_migration):
            next_internal_number += 1
            new_contract_reference = cls._generate_contract_reference(person, next_internal_number)
        return new_contract_reference

    @classmethod
    def _generate_contract_reference(cls, person, next_internal_number):
        new_contract_reference_digits = int(str(person.id) + str('%03d' % next_internal_number))
        luhn_key = cls._get_luhn_check_digit_of_number(new_contract_reference_digits)
        new_contract_reference = 'C' + str(new_contract_reference_digits) + str(luhn_key)
        return new_contract_reference

    @classmethod
    def _contract_reference_exists(cls, new_contract_reference, initial_migration=False):
        exists_in_lead = orm.exists(lead for lead in db.Lead if lead.future_contract_reference == new_contract_reference)
        if not initial_migration:
            exists_in_contracts = orm.exists(contract for contract in db.Contract if contract.reference == new_contract_reference)
            return exists_in_lead or exists_in_contracts
        else:
            return exists_in_lead

    @classmethod
    def _get_last_contract_number_for_person(cls, person, initial_migration):
        start_contract = 'C'+str(person.id)
        last_reference_from_leads = orm.select(lead.future_contract_reference for lead in db.Lead
                                          if lead.future_contract_reference is not None
                                          and lead.future_contract_reference != ''
                                          and lead.future_contract_reference.startswith(start_contract)
                                          and lead.person == person
                                          ).order_by(orm.desc(1)).first()
        last_from_lead = cls._get_last_contract_number(last_reference_from_leads)

        if not initial_migration:
            last_reference_from_contracts = orm.select(contract.reference for contract in db.Contract
                                             if contract.client.person == person
                                             and contract.reference.startswith(start_contract)).order_by(orm.desc(1)).first()
            last_from_contracts = cls._get_last_contract_number(last_reference_from_contracts)
        else:
            last_from_contracts = 0
        if last_from_lead > last_from_contracts:
            return last_from_lead
        else:
            return last_from_contracts

    @classmethod
    def _get_last_contract_number(cls, last_contract_reference):
        if last_contract_reference:
            ref_length = len(last_contract_reference)
            last_internal_number_str = last_contract_reference[ref_length-4:ref_length-1]
            return int(last_internal_number_str)
        else:
            return 0

    @classmethod
    def _get_luhn_check_digit_of_number(cls, number):
        number = number * 10
        digits = [int(d) for d in str(number)]
        odd_sum = sum(digits[-1::-2])
        even_sum = sum([sum(divmod(2 * d, 10)) for d in digits[-2::-2]])
        overall_sum = (odd_sum + even_sum)
        check_digit = int((10 - (overall_sum % 10)) % 10)
        return check_digit
