
from core_system.role.migrations.update_permissions import \
    generate_permission_list_from_dict
from core_system.role.models import ROLE_TYPE_IDS, Permission, Role
from core_system.role.permissions import all_permissions
from core_system.users.models.user_model import User
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService
from shared.services.base_service import BaseService


class RoleGetterService(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        return Role.select()


class PermissionService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, data_dict, user):
        role_name = data_dict.get('name')
        type = data_dict.get('type')
        permissions = data_dict.get('permissions')
        selected_permissions = cls._check_permissions(permissions, user, type)
        this_role = Role(
            name=role_name,
            permissions=selected_permissions,
            type=cls._get_type_id_from_type_name(type)
        )
        return this_role

    @classmethod
    def _edit_from_data_and_user(cls, role, data_dict, user):
        if role.name == 'SuperAdmin':
            raise Error('The SuperAdmin role can never be edited.')
        if role == user.get_role():
            raise Error('You cannot edit your own role.')
        if not cls.can_edit_role(user, role):
            raise Error('You are trying to edit a role with more permissions than you have.')
        role_name = data_dict.get('name')
        type = data_dict.get('type')
        permissions = data_dict.get('permissions')
        selected_permissions = cls._check_permissions(permissions, user, type)
        role.name = role_name
        role.type = cls._get_type_id_from_type_name(type)
        role.permissions = selected_permissions
        return role

    @classmethod
    def _delete_from_object_and_user(cls, role, user):
        if role.users.count() != 0:
            raise Error('You cannot delete a role that has users')
        role.delete()

    @classmethod
    def _get_type_id_from_type_name(cls, type_name):
        return ROLE_TYPE_IDS.get(type_name)

    @classmethod
    def _check_permissions(cls, permissions, user, type):
        selected_permissions = []
        if isinstance(permissions, dict):
            for permission in permissions:
                if permissions.get(permission) in [True, 'true', 'True', 1]:
                    selected_permissions.append(Permission.get(code_name=permission))
        else:
            for permission in permissions:
                selected_permissions.append(Permission.get(code_name=permission))
        if not cls.has_all_permission_in_list(user, selected_permissions):
            permissions_missing = cls.get_list_of_permissions_names_missing(
                user, selected_permissions
            )
            raise Error(
                'You are trying to give some permissions that you do not have.',
                permissions_missing=permissions_missing
            )
        if not Permission.has_one_required_permission(selected_permissions) and type != 'API':
            raise Error('You must tick at least "List Clients" or "View Leads" authorization before saving the role')
        return selected_permissions

    @classmethod
    def allowed_to_change_to_role(cls, user, role):
        return cls.has_all_permission_in_list(user, role.permissions)

    @classmethod
    def has_all_permission_in_list(cls, user, permission_list):
        if user.is_super_admin():
            return True
        user_permission_list = user.get_role().permissions
        all_permissions_list = set(generate_permission_list_from_dict(all_permissions))
        permission_list = [p for p in permission_list if p.code_name in all_permissions_list]
        # starting points from all permissions, this make sure any permission removed from the code
        # is not considered even if not removed from database for reversibility purposes
        return set(permission_list) <= set(user_permission_list)

    @classmethod
    def can_edit_role(cls, user, role):
        if role.name in ['SuperAdmin', 'Metrics API'] and user != User.get_system_user():
            return False
        return cls.has_all_permission_in_list(user, role.permissions)

    @classmethod
    def get_list_of_permissions_names_missing(cls, user, permission_list):
        permission_missing_list = []
        user_permission_list = user.get_role().permissions
        for permission in permission_list:
            if permission not in user_permission_list:
                permission_missing_list.append(permission.code_name)
        return permission_missing_list

    @classmethod
    def get_allowed_roles_for_user(cls, user):
        all_roles = Role.select()
        allowed_roles_id = []
        for role in all_roles:
            if cls.allowed_to_change_to_role(user, role):
                allowed_roles_id.append(role.id)
        return Role.select().filter(lambda r: r.id in allowed_roles_id)
