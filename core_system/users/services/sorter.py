from shared.services.sorter import Sorter
from pony import orm


class UserSorter(Sorter):

    @classmethod
    def sort_by(cls, field_name):
        options = {
        }
        return options.get(field_name, lambda u: u.id)

    @staticmethod
    def real_field_sort(field_name, desc=False):
        options = {
            'id': lambda u: u.id,
            'full_name': lambda u: u.person.searchable_name,
            'username': lambda u: u.username,
            'email': lambda u: u.email,
            'organization': lambda u: u.organization,
            'role': lambda u: u.AuthorizationLevel.name,
            'expiration_date': lambda u: u.loginExpirationDate,
            'ref_entity': lambda u: u.shop.name,
        }
        options_desc = {
            'id': lambda u: orm.desc(u.id),
            'full_name': lambda u: orm.desc(u.person.searchable_name),
            'username': lambda u: orm.desc(u.username),
            'email': lambda u: orm.desc(u.email),
            'organization': lambda u: orm.desc(u.organization),
            'role': lambda u: orm.desc(u.AuthorizationLevel.name),
            'expiration_date': lambda u: orm.desc(u.loginExpirationDate),
            'ref_entity': lambda u: orm.desc(u.shop.name),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, lambda E: E.person.name))
        return options.get(field_name, lambda u: u.id)
