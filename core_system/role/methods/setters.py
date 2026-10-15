from pony.orm import *
from core_system.role.models import Role, Permission
from core_system.role.permissions import associated_permissions, associated_roles
from core_system.role.default_permissions import admin_permissions
from shared.logger.loggers import Error

managers = ['Manager', 'Accountant', 'SuperManager']
mentors = ['Mentor']
other = ['Retailer', 'SuperGuest', 'Guest', 'LeadGenerator', 'ViewOnly']
admin = ['SuperAdmin', 'Admin']

admin_permissions_list = [p+cat for cat, perms in admin_permissions.items() for p in perms]


def get_role_type(role_name):
    """
    Written by Andrew Graham-Yooll
    June 6, 2017

    This function will return the category type number for the type of role that is passed through.

    To be used mainly in migrations which it was originally designed for.

    This function is NOT dynamic, so any use of this method should be carefully constructed to suit the users needs.

    :param role_name:
    :return:
    """
    if role_name in managers:
        return 1
    elif role_name in mentors:
        return 2
    elif role_name in other:
        return 0
    elif role_name in admin:
        return 3
    else:
        print("Error: The role name was not found to be part of any type category.")


def create_role_in_db(role_name, permissions, type=None):
    if type is None:
        type = get_role_type(role_name)

    Role(name=role_name,
         permissions=permissions,
         type=type)

    commit()


def create_permission(permission_name, code_name, max_value=None, min_value=None):
    p = Permission(name=permission_name,
                   code_name=code_name,
                   max_value=max_value,
                   min_value=min_value)
    commit()
    return p


def associate_related_permission(this_permission):
    code_name = this_permission.code_name
    all_associated_permission_names = associated_permissions.get(code_name, [])
    print(f'Associating roles to: {code_name}')
    all_associated_permissions = select(perm for perm in Permission if perm.code_name in all_associated_permission_names)
    for permission in all_associated_permissions:
        associate_permission_to_roles(this_permission, permission.roles)
    # add to migrated roles and admin roles
    roles_names = associated_roles.get(code_name, []) + ['SuperAdmin']
    if code_name in admin_permissions_list:
        roles_names += ['Admin']
    roles = [Role.get(name=name) for name in roles_names if Role.get(name=name)]
    associate_permission_to_roles(this_permission, roles)


def associate_permission_to_roles(permission, roles):
    for role in roles:
        if permission not in role.permissions:
            print(f'Adding permission {permission.code_name} to role {role.name}. ')
            role.permissions.add(permission)


def bulk_delete_roles(role_id_list):
    for role_id in role_id_list:
        role = Role.get(id=role_id)
        if role_can_be_deleted(role):
            role.delete()
    commit()


def role_can_be_deleted(role):
    if count(role.users) != 0:
        raise Error('CANT_DELETE_ROLE_WITH_USERS')
    return True


def edit_role_from_form(role, name, type, permissions):
    role.name = name
    role.type = type
    role.permissions = permissions
    commit()
