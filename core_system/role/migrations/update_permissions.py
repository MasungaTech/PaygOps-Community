from core_system.role.permissions import all_permissions, renamed_permissions, deleted_permissions, metrics_api_permissions
import re
from core_system.role.methods.setters import create_permission, associate_related_permission
from core_system.role.models import Permission, Role
from pony import orm
from core_system.role.methods.getters import get_role_from_name, get_all_permissions, get_permission_objects_from_list_of_names


def generate_permission_list_from_dict(permission_dict):
    all_permissions = []
    for pgk, pgv in permission_dict.items():
        for v in pgv:
            all_permissions.append(str(v + pgk))

    return all_permissions


def check_and_create_missing_permissions():
    all_permissions_list = generate_permission_list_from_dict(all_permissions)
    for permission in all_permissions_list:
        name = ' '.join(re.findall('[A-Z][^A-Z]*', permission))
        permission_object = orm.select(P for P in Permission if P.code_name == permission).first()
        if not permission_object:
            print('Installing permission: ' + permission)
            this_permission = create_permission(name, permission)
            orm.flush()
            associate_related_permission(this_permission)
        else:
            # Ensuring that the names are correct after renaming or other operations
            if permission_object.name != name:
                permission_object.name = name
        orm.commit()


def change_permission_names():
    for permission_key, permission_value in renamed_permissions.items():
        this_permission = Permission.get(code_name=permission_key)
        if this_permission is not None:
            this_permission.code_name = permission_value
        else:
            print('Permission ' + permission_key + ' already migrated. ')


def delete_old_permissions():
    for permission in deleted_permissions:
        this_permission = Permission.get(code_name=permission)
        if this_permission is not None:
            this_permission.delete()
        else:
            pass # No need to print for now
            #print('Permission ' + permission + ' already deleted. ')


def assign_all_permissions_to_superadmin():
    super_admin_role = get_role_from_name('SuperAdmin')
    if not super_admin_role:
        super_admin_role = Role(name='SuperAdmin', type=3)
    all_permissions_obj = get_all_permissions()
    for p in all_permissions_obj:
        super_admin_role.permissions += p
    # We ensure that metrics role also always has correct permissions
    metrics_role = get_role_from_name('Metrics API')
    if not metrics_role:
        metrics_role = Role(name='Metrics API', type=4)
    # Overwrite (not append) to keep this role deterministic across deployments.
    metrics_role.permissions = get_permission_objects_from_list_of_names(metrics_api_permissions)


AUTO_DELETE_PERMISSIONS = True

def check_permission_integrity():
    all_permissions_list = generate_permission_list_from_dict(all_permissions)
    all_permissions_obj = get_all_permissions()
    for p in all_permissions_obj:
        if p.code_name not in all_permissions_list:
            print('Warning! Permission ' + p.code_name + ' should be deleted!')


@orm.db_session
def update_permissions():
    delete_old_permissions()
    change_permission_names()
    check_and_create_missing_permissions()
    assign_all_permissions_to_superadmin()
    check_permission_integrity()
