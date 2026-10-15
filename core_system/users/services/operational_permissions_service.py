from core_system.operational_entities.models import UserWithRole
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from core_system.role.models import Role
from core_system.role.services import PermissionService, RoleGetterService
from core_system.users.services.user_getter_service import UserGetterService
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService


class OperationalPermissionsService(BaseGetterService):

    OBJ_NAME = 'Operational Permission'

    @classmethod
    def preprocess_list_filters(cls, current_user, **kwargs):
        if kwargs['user_id']:
            user = UserGetterService.get_from_user_and_id(current_user, id=kwargs['user_id'], strict=True)
            kwargs['user'] = user
        return kwargs

    @classmethod
    def get_filtered_objects(cls, current_user, user=None, **kwargs):
        users = UserGetterService.get_list(current_user)
        if user:
            users = users.filter(lambda u: u == user)
        return UserWithRole.select(lambda uwr: uwr.user in users)

    @classmethod
    def get_affected_entity(cls, data, current_user, **kwargs):
        return OperationalEntitiesGetterService.extract_from_user_and_id(current_user, data, 'entity_id', strict=False)
    
    @classmethod
    def _add_from_data_and_user(cls, data, current_user):
        cls.check_if_data_is_valid(data, current_user)
        user = UserGetterService.extract_from_user_and_id(current_user, data, 'user_id', strict=True, empty_allowed=False)
        entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, data, 'entity_id', strict=False)
        role = RoleGetterService.get_from_user_and_id(current_user, data.get('role_id') or -1)
        sync_enabled = data.get('sync_enabled', False)
        # We automatically create a default role in all for Super Admins as needed
        if user.is_super_admin() and user.roles_in_entities.filter(lambda rie: rie.entity == None and rie.role == None).count() == 0:
            user.roles_in_entities.create(entity=None, role=None, sync_entity=False)
        return UserWithRole(user=user, role=role, entity=entity, sync_entity=sync_enabled)
    
    @classmethod
    def _edit_from_data_and_user(cls, rie, data, current_user):
        cls.check_if_data_is_valid(data, current_user, rie)
        if 'role_id' in data:
            role = RoleGetterService.get_from_user_and_id(current_user, data['role_id'])
            rie.role = role
        if data.get('entity_id'):
            entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, data, 'entity_id', strict=False)
            rie.entity = entity
        if 'sync_enabled' in data:
            rie.sync_entity = data.get('sync_enabled', False)
        return rie
    
    @classmethod
    def check_if_data_is_valid(cls, data, current_user, rie=None):
        user = UserGetterService.extract_from_user_and_id(current_user, data, 'user_id', strict=False)
        if 'user_id' in data and not user:
            raise Error('User ID provided is invalid or you do not have the permission for it. ')
        if not user and rie:
            user = rie.user
        if not user:
            raise Error('User must be provided')
        entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, data, 'entity_id', strict=False)
        if data.get('entity_id') and not entity:
            raise Error('Entity ID provided is invalid or you do not have the permission for it. ')
        if not entity and rie and rie.entity:
            entity = rie.entity
        if data.get('entity_type') == 'all' and entity:
            raise Error('You cannot specify an entity if you want the permission to be for "all"')
        is_all = (data.get('entity_type') == 'all') or not entity and not data.get('entity_id')
        if is_all:
            if not current_user.can_access_in_all('EditUsers'):
                raise Error('You do not have the permissions to add or edit roles in "all". ')
            if data.get('sync_enabled', False):
                raise Error('Cannot enable sync in all entities', code="CANNOT_SYNC_ALL_ENTITIES")
        else:
            if not entity:
                raise Error('You must specify an entity if entity type is not "all". ')
        if entity and entity.level > OperationalEntitiesHelper.get_max_level_enabled():
            raise Error('Entity '+entity.name+' is not enabled', code="ENTITY_NOT_ENABLED")
        # We get the role or the default role if none is provided
        role = RoleGetterService.get_from_user_and_id(current_user, data.get('role_id'))
        if not role:
            if rie and rie.role:
                role = rie.role
            else:
                role = user.AuthorizationLevel
        if not PermissionService.allowed_to_change_to_role(current_user, role):
            raise Error(f"You cannot give role {role.name} in {entity.name if entity else 'All'} as it has more permissions than your default role.", code="CANNOT_ASSIGN_HIGHER_ROLE")
        # If the user has entities already and its not the one we're editing
        if not rie or rie.entity != entity:
            # We check if we're not giving a duplicate role in entity
            if user.roles_in_entities.filter(lambda nrie: nrie.entity == entity).exists():
                raise Error(f"User {user.full_name} already has a role in {entity.name if entity else 'All'}", code="USER_ALREADY_HAS_ROLE")

    @classmethod
    def _delete_from_object_and_user(cls, rie, current_user):
        if rie.user.roles_in_entities.count() == 1:
            raise Error("You cannot delete the last operational permission", code="CANNOT_DELETE_LAST_OPERATIONAL_PERMISSION")
        if rie.user.is_super_admin() and not rie.entity and not rie.role:
            raise Error("You cannot delete the super admin role in All", code="CANNOT_DELETE_SUPER_ADMIN_ROLE_IN_ALL")
        rie.delete()

    @classmethod
    def copy_user_permission(cls, user_making_action, origin_user, destination_user):
        origin_user_roles = origin_user.roles_in_entities
        for origin_user_role in origin_user_roles:
            if not destination_user.roles_in_entities.filter(lambda rie: rie.entity == origin_user_role.entity).exists():
                cls.add_from_data_and_user({
                    'user_id': destination_user.id,
                    'role_id': origin_user_role.role.id if origin_user_role.role else None,
                    'entity_id': origin_user_role.entity.id if origin_user_role.entity else None,
                    'sync_enabled': origin_user_role.sync_entity
                }, user_making_action)

