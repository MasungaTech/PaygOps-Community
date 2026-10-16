from core_system.operational_entities.models import OperationalEntity
from shared.services.sorter import Sorter
from pony import orm


class OperationalEntitySorter(Sorter):

    def sort_by(field_name):
        options = {
            'user_in_charge': lambda e: e.inherited_user_in_charge.full_name,
            'leads': lambda e: e.get_active_leads().count(),
            'clients': lambda e: e.get_clients().count(),
            'children': lambda e: e.children.count(),
        }
        return options.get(field_name, OperationalEntity.id)

    def real_field_sort(field_name, desc=False):
        options = {
            'id': OperationalEntity.id,
            'name': OperationalEntity.name,
            'parent': lambda e: e.parent.name,
            'leads': False,
            'clients': False,
            'user_in_charge': False,
            'children': False,
        }
        options_desc = {
            'parent': lambda e: orm.desc(e.parent.name),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, OperationalEntity.id))
        return options.get(field_name, OperationalEntity.id)

