from core_system.role.default_permissions import admin_permissions, accountant_permissions, \
    super_manager_permissions, manager_permissions, agent_permissions, viewonly_permissions, billing_api_permissions
from core_system.role.methods.getters import get_permission_objects_from_list_of_names
from core_system.role.migrations.update_permissions import generate_permission_list_from_dict, \
    check_and_create_missing_permissions
from core_system.role.models import Permission, Role
from core_system.role.permissions import all_permissions
from pony.orm import *


def create_role_in_db(role_name, permission_dict=None, type=None, permission_list=None, overwrite=False):
    if not permission_list:
        permission_list = generate_permission_list_from_dict(permission_dict)
    permissions = Permission.select(lambda p: p.code_name in permission_list)
    db_perms_list = [p.code_name for p in permissions]

    for p in permission_list:
        if p not in db_perms_list:
            raise Exception('Permission '+p+' not declared')

    existing_role = Role.select(lambda r: r.name == role_name).first()
    if existing_role:
        if overwrite:
            existing_role.permissions = permissions
            existing_role.type = type
        else:
            raise Exception('Role '+role_name+' already exists')
    else:
        Role(
            name=role_name,
            permissions=permissions,
            type=type
        )
    commit()


def create_roles():
    create_role_in_db('SuperAdmin', all_permissions, 3)
    create_role_in_db('Admin', admin_permissions, 3)
    create_role_in_db('Accountant', accountant_permissions, 2)
    create_role_in_db('SuperManager', super_manager_permissions, 2)
    create_role_in_db('Manager', manager_permissions, 2)
    create_role_in_db('Agent', agent_permissions, 1)
    create_role_in_db('ViewOnly', viewonly_permissions, 0)
    # Metrics API role is expected to be deterministic across deployments.
    # If it already exists, overwrite its permissions.
    create_role_in_db('Metrics API', billing_api_permissions, 4, overwrite=True)


@db_session
def install_permissions():
    try:
        check_and_create_missing_permissions()
        flush()
        create_roles()
        flush()
    except Exception as e:
        rollback()
        print('error', str(e))
        raise e

    commit()
