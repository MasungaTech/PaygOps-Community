from decimal import Decimal
from constants import OPERATIONAL_ENTITIES_CONFIG
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from core_system.users.models.user_model import User
from shared.services.background_task_base import BackgroundTask
from pony import orm
from worker_app.worker_app import worker_app

HEADER = [
    'Level 0', 'Level 1', 'Level 2', 'Level 3', 'Level 4', 'User In Charge ID', 'GPS Longitude', 'GPS Latitude',
    'Administrative Contact Name', 'Administrative Contact Number', 'Population', 'Description'
]

class NewOperationalEntity:

    def __init__(self, name, level, parent=None):
        self.name = name
        self.level = level
        self.parent = parent
        self.children = []
    
    def __repr__(self):
        return f'{self.name}[{self.level}@{self.parent}]'
    

## Code for generating the resulting hierarchical structure
## Not working but is almost there, left here cause is likely to be required

# def get_data(entity):
#     return {
#         'name': entity.name,
#         'children': [get_data(e) for e in entity.children]
#     }

# def get_partial_structure(tles):
#     ancestors = []
#     entity = tles[0]
#     parent = entity
#     while parent:
#         ancestors.append(parent)
#         parent = parent.parent
#     def s(i):
#         lower_level, subchildren = s(i-1) if i > 1 else None, []
#         children = [e for e in tles if e.parent == ancestors[i]]
#         return {
#             'name': ancestors[i].name,
#             'children': [get_data(e) for e in children] + ([lower_level] if lower_level else [])
#         }, children + subchildren
#     data, used = s(len(ancestors)-1)
#     remaining = [e for e in tles if e not in used]
#     return [data] + (get_partial_structure(remaining) if remaining else [])


@worker_app.task
@orm.db_session
def analyse_bulk_operational_entities(task_uuid):

    print('Analysing bulk operational entities...')
    task_service = BackgroundTask(task_uuid)
    acting_user = User.get(id=task_service.user)
    file = task_service.read_csv_file()

    level_counts = {i: 0 for i in range(0, len(OPERATIONAL_ENTITIES_CONFIG))}
    max_level = OperationalEntitiesHelper.get_max_level_enabled()

    correct_entities = 0
    total_entities = 0
    data = []
    errors = {}
    new_entities = []

    for line in file:

        line = [x.strip() for x in line]
        if total_entities == 0 and [h.lower() for h in line] == [h.lower() for h in HEADER]:
            continue
        total_entities += 1

        lenofline = len(line)
        if not(5 <= lenofline <= 12):
            errors[total_entities] = f'Incorrect format, the row must have between 5 and 12 columns.'
            continue

        entities_names = line[4::-1]

        lower_entity = None
        parent = None
        level = 5
        correct = True
        for entity_name in entities_names:
            level -= 1
            if level > max_level:
                lower_entity = OperationalEntitiesGetterService.get_from_user_and_properties(acting_user, level=level).name
                continue
            if entity_name:
                if lower_entity:
                    # print(f'Looking parent for {entity_name}')
                    if not parent:
                        # print('There is no previous parent, looking at top level')
                        parent = OperationalEntitiesGetterService.get_from_user_and_properties(acting_user, name=lower_entity, level=level+1)
                        if not parent:
                            # print('No top level parent in db')
                            parent_list = [e for e in new_entities if e.name == lower_entity and e.level == level+1]
                            parent = parent_list[0] if parent_list else None
                    elif isinstance(parent, NewOperationalEntity):
                        # print('Previous Parent is to be added')
                        parent_list = [e for e in parent.children if e.name == lower_entity]
                        parent = parent_list[0] if parent_list else None
                    else:
                        # print('Previous Parent exists in db, looking for current parent in its children')
                        old_parent = parent
                        parent = old_parent.children.filter(lambda e: e.name == lower_entity).first()
                        if not parent:
                            # print('Current parent not found its db children, looking in objs')
                            parent_list = [e for e in new_entities if e.name == lower_entity and e.parent == old_parent]
                            # print(old_parent.id)
                            # print([e.parent for e in new_entities if e.name == lower_entity.strip()])
                            parent = parent_list[0] if parent_list else None
                    if not parent:
                        errors[total_entities] = f'Parent Entity {lower_entity} was not found'
                        correct = False
                        break
                lower_entity = entity_name

            elif any(entities_names[5-level:]):
                errors[total_entities] = f'There are some missing ancestors (at least level {level})'
                correct = False
                break
            else: 
                level += 1 # we went to the next level down but was empty so return one up
                break
        if not correct:
            continue

        check_permissions = level == 4 or not isinstance(parent, NewOperationalEntity)
        if check_permissions and not acting_user.can_access('Add'+OperationalEntitiesHelper.get_permission_name(level), entity=parent):
            errors[total_entities] = f'You don\'t have permissions to add entities in {parent.name}' if parent else f'You don\'t have permissions to add entities in level 4'
            correct = False
            break

        if parent:
            existing = [e for e in new_entities if e.name == lower_entity and e.parent == parent]
            if existing:
                errors[total_entities] = f'Entity {lower_entity} is created twice in this file ' + (f' in {parent.name}' if level != 4 else '')
                continue
            if not isinstance(parent, NewOperationalEntity):
                existing = parent.children.filter(lambda e: e.name == lower_entity).first()
                if existing:
                    errors[total_entities] = f'Entity {lower_entity} already exists in the platform ' + (f' in {parent.name}' if level != 4 else '')
                    continue
        else:
            existing = OperationalEntitiesGetterService.get_from_user_and_properties(acting_user, name=lower_entity, level=level)
            if existing:
                errors[total_entities] = f'Entity {lower_entity} already existis at level {level}'
                continue

        def g(i):
            return line[i] if lenofline > i else ''

        user_in_charge_id = g(5)
        user_in_charge = None
        if user_in_charge_id:
            user_in_charge = User.get(id=user_in_charge_id)
        
        if level == max_level and not user_in_charge:
            errors[total_entities] = f'Entity {lower_entity} missing user in charge or user not found'
            continue

        gps_lat = g(6)
        gps_lon = g(7)

        if gps_lat or gps_lon:
            try:
                Decimal(gps_lat)
                Decimal(gps_lon)
            except Exception:
                errors[total_entities] = f'Invalid gps coordinates format "({gps_lat},{gps_lon})"'
                continue

        new_entity = NewOperationalEntity(
            lower_entity,
            level,
            parent
        )

        new_entities.append(new_entity)
        if isinstance(parent, NewOperationalEntity):
            parent.children.append(new_entity)

        admin_name = g(8) 
        admin_number = g(9)
        population = g(10)
        description = g(11)

        correct_entities += 1

        level_counts[level] += 1
        data.append(line[0:5] + [user_in_charge_id, gps_lat, gps_lon, admin_name, admin_number, population, description])

    # structure = [get_data(e) for e in new_entities if e.level == 4]
    # top_level_entities = [e for e in new_entities if not isinstance(e.parent, NewOperationalEntity) and e.level != 4]
    # structure += get_partial_structure(top_level_entities)

    task_service.complete_analysis({
        'correct_entities': correct_entities,
        'total_entities': total_entities,
        'level_counts': level_counts,
        'errors': errors
    }, data)
