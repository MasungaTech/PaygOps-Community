from shared.services.sorter import Sorter
from pony import orm


class AddonOfferSorter(Sorter):

    @classmethod
    def sort_by(cls, field_name):
        options = {
        }
        return options.get(field_name, lambda u: u.id)

    @staticmethod
    def real_field_sort(field_name, desc=False):
        options = {
            'id': lambda o: o.id,
            'code': lambda o: o.code,
            'name': lambda o: o.name,
            'category': lambda o: o.category.name,
            'needs_approval': lambda o: o.need_approval,
            'type': lambda o: o.type,
        }
        options_desc = {
            'id': lambda o: orm.desc(o.id),
            'code': lambda o: orm.desc(o.code),
            'name': lambda o: orm.desc(o.name),
            'category': lambda o: orm.desc(o.category.name),
            'needs_approval': lambda o: orm.desc(o.need_approval),
            'type': lambda o: orm.desc(o.type),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, lambda E: E.person.name))
        return options.get(field_name, lambda u: u.id)
