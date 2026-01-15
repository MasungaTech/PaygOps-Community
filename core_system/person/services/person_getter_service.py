from core_system.person.models.person_model import Person, PersonType
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.phone_numbers.services.phone_number_getter import PhoneNumberGetterService
from shared.services.base_getter_service import BaseGetterService
from pony.orm import select, left_join
from shared.helpers.db_helpers import searchable_text


class PersonGetterService(BaseGetterService):

    OBJ_NAME = 'Person'

    @classmethod
    def get_persons_with_permission(cls, current_user, permission, for_sync=False, managed_by=None):
        persons = left_join(p for p in Person)
        if for_sync or not current_user.can_access_in_all(permission):
            villages_ids, client_groups_ids = current_user.get_villages_and_client_groups_with_permission(permission, for_sync=for_sync, managed_by=managed_by, return_villages_ids=True)
            if client_groups_ids:
                persons = persons.filter(lambda p: p.village.id in villages_ids or p.client_group.id in client_groups_ids)
            else:
                persons = persons.filter(lambda p: p.village.id in villages_ids)
        return persons

    @classmethod
    def get_filtered_objects(
        cls, current_user, permission, entity=None, managed_by=None, generated_by=None, portfolio=None,
        created_by=None, phone_number=None, client_group=None, extra_permission=None, for_sync=False, search=None, **kwargs
    ):

        current_user = current_user.reload()
        persons = cls.get_persons_with_permission(current_user, permission, for_sync=for_sync, managed_by=managed_by)
        if extra_permission:
            if not isinstance(extra_permission, list):
                extra_permission = [extra_permission]
            for per in extra_permission:
                persons = persons.filter(lambda p: p in cls.get_persons_with_permission(current_user, per, for_sync=for_sync, managed_by=managed_by))
        if entity:
            persons = persons.filter(lambda p: p.village in entity.descendants)
        if generated_by:
            persons = persons.filter(lambda p: generated_by.person.leadGenerator in select(l.generator for l in p.lead))
        if created_by:
            persons = persons.filter(lambda p: created_by in select(l.reporter for l in p.lead))
        if client_group:
            persons = persons.filter(lambda p: p.client_group == client_group)
        if phone_number:
            number_persons = PhoneNumberGetterService.find_persons_if_search_is_number(phone_number)
            persons = persons.filter(lambda p: p in number_persons)
        if portfolio:
            persons = persons.filter(lambda p: (
                p.lead.select(lambda l: l.portfolio == portfolio).count() > 0 or
                p.client.contracts.select(lambda c: c.portfolio == portfolio).count() > 0
            ))
        if search:
            number_persons = PhoneNumberGetterService.find_persons_if_search_is_number(phone_number)
            clean_search = searchable_text(search)
            persons = persons.filter(lambda p: 
                p in number_persons or
                clean_search in p.searchable_name or
                search in p.custom_id
            )
        return persons

