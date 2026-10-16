from shared.services.sorter import Sorter
from pony import orm


class AddonBundleSorter(Sorter):

    @classmethod
    def sort_by(cls, field_name):
        options = {
        }
        return options.get(field_name, lambda u: u.id)

    @staticmethod
    def real_field_sort(field_name, desc=False):
        options = {
            'id': lambda o: o.id,
            'name': lambda o: o.name,
            'available_for_sales': lambda o: o.cached_available_for_leads,
            'available_for_registration': lambda o: o.cached_available_for_contracts,
        }
        options_desc = {
            'id': lambda o: orm.desc(o.id),
            'name': lambda o: orm.desc(o.name),
            'available_for_sales': lambda o: orm.desc(o.cached_available_for_leads),
            'available_for_registration': lambda o: orm.desc(o.cached_available_for_contracts),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, lambda E: E.person.name))
        return options.get(field_name, lambda u: u.id)
