from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from core_system.users.services.user_getter_service import UserGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from core_system.client.services.client_getter_service import ClientGetterService
from shared.services.base_getter_service import BaseGetterService
from core_system.phone_numbers.model import PhoneNumbers
from sales_system.leads.models.lead import Lead
from pony import orm


class PhoneNumberGetterService(BaseGetterService):

    OBJ_NAME = 'Phone Number'

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        clients = orm.select(c.person for c in ClientGetterService.get_list(current_user))
        leads = orm.select(l.person for l in LeadGetterService.get_list(current_user))
        users = orm.select(u.person for u in UserGetterService.get_list(current_user))
        generators = orm.select(g.person for g in LeadGeneratorGetterService.get_list(current_user))
        numbers = PhoneNumbers.select(
            lambda n: orm.exists(p for p in n.persons if p.client or p.user or p.leadGenerator or p.lead)
        )
        numbers = numbers.filter(
            lambda n: orm.exists(p for p in n.persons if p in clients or p in leads or p in users or p in generators)
        )
        return numbers

    @classmethod
    def get_phone_number(cls, number):
        if number:
            number = cls._clean_number(number)
            return cls.get_by_number(number)
        return None

    @classmethod
    def find_phone_numbers(cls, partial_number):
        return orm.select(
            number for number in PhoneNumbers
            if partial_number in number.number and orm.exists(
                p for p in number.persons if p.client or p.user or p.leadGenerator or p.lead
            )
        )

    @classmethod
    def get_by_number(cls, number):
        return PhoneNumbers.get(number=number)

    @classmethod
    def _clean_number(cls, number):
        if number:
            try:
                number = '+'+str(int(number))
            except ValueError as e:
                pass
        return number

    @classmethod
    def get_client_by_phone_number(cls, number):
        phone = cls.get_phone_number(number)
        owner = cls._profile_owners(phone).filter(lambda p: p.client).first() if phone else None
        return owner.client if owner else None

    @classmethod
    def get_leads_by_phone_number(cls, number):
        phone = cls.get_phone_number(number)
        if not phone:
            return None
        return orm.select(lead for lead in Lead if lead.person in phone.persons)

    @classmethod
    def find_persons_if_search_is_number(cls, number):
        if not number:
            return []
        number = number.replace('+', '').replace(' ', '')
        owners = set()
        for phone in cls.find_phone_numbers(number):
            owners.update(phone.persons)
            if phone.person is not None:
                owners.add(phone.person)
        return list(owners)
        return cls._profile_owners(numbers.first())

    @staticmethod
    def _profile_owners(number):
        return number.persons.select(
            lambda p: p.client or p.user or p.leadGenerator or p.lead
        )
