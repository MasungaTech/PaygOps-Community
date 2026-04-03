from core_system.operational_entities.models import ClientGroup
from shared.services.sorter import Sorter


class ClientGroupSorter(Sorter):
    def sort_by(field_name):
        options = {
            'user_in_charge': lambda g: g.user_in_charge.full_name,
        }

        return options.get(field_name, ClientGroup.id)

    def real_field_sort(field_name, desc=False):
        options = {
            'id': ClientGroup.id,
            'name': ClientGroup.name,
            'user_in_charge': False,
        }
        return options.get(field_name, ClientGroup.id)

