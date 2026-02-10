from constants import ENTITIES_OLD_ID_OFFSET, MAX_ENTITY_LEVEL
from core_system.users.models.user_model import User
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from core_system.users.services.user_getter_service import UserGetterService
from shared.logger.loggers import Error
from core_system.operational_entities.models import HierarchicalOperationalEntity
from shared.helpers.picture_helper import storePicture, getGPSCoordinatesFromPicture
from pony import orm

from shared.services.settings_service import SettingsService
from shared.services.base_service import BaseService


class EditOperationalEntityService(BaseService):
    
    @classmethod
    def _add_from_data_and_user(cls, data, user, check_permissions=True):
        name = data.get('name')
        if not name:
            raise Error('The name is required.')
        level = int(data.get('level'))
        if level not in [0, 1, 2, 3, 4]:
            raise Error('Invalid level')
        parent = HierarchicalOperationalEntity.get(id=data.get('parent_id'))   
        if parent and parent.level != level+1:
            raise Error('Invalid parent, must be excalty one level above the entity')
        if not parent and level == OperationalEntitiesHelper.get_max_level_enabled() and level < MAX_ENTITY_LEVEL:
            parent = HierarchicalOperationalEntity.get(level=level+1)
        if check_permissions and not user.can_access('Add'+OperationalEntitiesHelper.get_permission_name(level), entity=parent):
            raise Error('Not enough permission to add entity of level '+str(level))     
        cls._check_if_name_exists(name, parent)
        user_in_charge = None
        if data.get('user_in_charge_id'):
            user_in_charge = UserGetterService.get_from_user_and_id(user, data['user_in_charge_id'], strict=True)
        if level == OperationalEntitiesHelper.get_max_level_enabled() and not user_in_charge:
            raise Error('User in charge required for highest level')
        entity = OperationalEntitiesHelper.get_level_class(level)(
            name=data.get('name'),
            parent=parent,
            longitude=float(data.get('gps_longitude')) if data.get('gps_longitude') else None,
            latitude=float(data.get('gps_latitude')) if data.get('gps_latitude') else None,
            admin_contact_name=data.get('admin_contact_name', ''),
            admin_phone_number=data.get('admin_phone_number', ''),
            population=int(data.get('population')) if data.get('population') else None,
            description=data.get('description', ''),
            user_in_charge=user_in_charge
        )
        if user_in_charge:
            entity.users_with_roles.create(user=user_in_charge, sync_entity=SettingsService.get_setting('SyncEntityByDefaultForNewUsersInCharge'))
        orm.flush()
        entity.code = str(entity.id + ENTITIES_OLD_ID_OFFSET)
        return entity

    @classmethod
    def _edit_from_data_and_user(cls, entity, data, user):
        if user and not user.can_access('Edit'+OperationalEntitiesHelper.get_permission_name(entity.level), entity=entity):
            raise Error('Not enough permission to edit entity '+entity.name) 
        parent = HierarchicalOperationalEntity.get(id=data.get('parent_id'))
        if data.get('parent_id') and not parent:
            raise Error('A valid parent ID is required.')
        name = data.get('name', entity.name)
        cls._check_if_name_exists(name, parent or entity.parent, editing=entity)        
        entity.name = name
        if 'parent_id' in data:
            entity.parent = parent
        entity.admin_contact_name = data.get('admin_contact_name', entity.admin_contact_name)
        entity.admin_phone_number = data.get('admin_phone_number', entity.admin_phone_number)
        entity.longitude = cls._convert_if_present('gps_longitude', data, 'float', entity.longitude)
        entity.latitude = cls._convert_if_present('gps_latitude', data, 'float', entity.latitude)
        entity.population = cls._convert_if_present('population', data, 'int', entity.population)
        if 'description' in data:
            entity.description = data['description'] or ''

        if 'user_in_charge_id' in data:
            user_in_charge = UserGetterService.extract_from_user_and_id(user, data, 'user_in_charge_id')
            if entity.level == OperationalEntitiesHelper.get_max_level_enabled() and not user_in_charge:
                raise Error('User in charge required for highest level')
            if user_in_charge and entity.user_in_charge != user_in_charge and not entity.users_with_roles.select(lambda uwr: uwr.user == user_in_charge).exists():
                entity.users_with_roles.create(user=user_in_charge, sync_entity=SettingsService.get_setting('SyncEntityByDefaultForNewUsersInCharge'))
            entity.user_in_charge = user_in_charge

        picture_uuid = data.get('picture_id')
        if picture_uuid:
            cls._update_gps_coordinates_from_picture(entity, picture_uuid)

    @classmethod
    def _delete_from_object_and_user(cls, entity, user):
        if not user.can_access('Delete'+OperationalEntitiesHelper.ENTITY_LEVELS_MAPPING[entity.level].capitalize(), entity=entity):
            raise Error('Not enough permission to delete entity '+entity.name)
        if entity.children:
            raise Error('Cannot delete entity with children entities')
        if entity.notifications:
            raise Error('Cannot delete entity with notifications associated')
        if entity.destined_stock:
            raise Error('Cannot delete entity with stock items associated to it')
        if entity.reference_of_users:
            raise Error('Cannot delete entity with Users that have it as reference entity')
        for uwr in entity.users_with_roles:
            uwr.delete()
        entity.delete()
        
    @classmethod
    def _convert_if_present(cls, value_name, data, data_type, default):
        result = data.get(value_name, default)
        if result:
            return int(result) if data_type == 'int' else float(result)
        return None

    @classmethod
    def _update_gps_coordinates_from_picture(cls, entity, picture_uuid):
        this_picture = storePicture(picture_uuid)
        if this_picture is not None:
            gps_coordinates = getGPSCoordinatesFromPicture(this_picture)
            if gps_coordinates is not None:
                entity.latitude = gps_coordinates[0]
                entity.longitude = gps_coordinates[1]
    @classmethod
    def _check_if_name_exists(cls, name, parent, editing=None):
        matching_entity = HierarchicalOperationalEntity.select(
            lambda oe: oe.name == name and oe.parent == parent and oe != editing
        )
        if matching_entity.exists():
            raise Error('The name is already in use by a entity with the same parent.')

    @classmethod
    def get_affected_entity(cls, data, user, id=None, **kwargs):
        if id:
            return HierarchicalOperationalEntity.get(id=id)
        level = int(data.get('level'))
        if level not in [0, 1, 2, 3, 4]:
            raise Error('Invalid level')
        parent = HierarchicalOperationalEntity.get(id=data.get('parent_id'))  
        if parent and parent.level != level+1:
            raise Error('Invalid parent, must be exactly one level above the entity')
        if not parent and level == OperationalEntitiesHelper.get_max_level_enabled() and level < MAX_ENTITY_LEVEL:
            parent = HierarchicalOperationalEntity.get(level=level+1)
        if not parent and level != MAX_ENTITY_LEVEL:
            raise Error('Invalid parent, must be a valid entity')
        return parent
