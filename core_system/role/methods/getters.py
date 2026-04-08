from core_system.role.models import Permission, Role, RoleType, get_role_type_name, ROLE_TYPE_IDS
from pony.orm import db_session


def get_permission_objects_from_list_of_names(list_of_names):
    """
    Written by Andrew Graham-Yooll

    Takes a list of valid permission names (code_names) and returns a list of Permission objects.

    This can be used to create a bulk relation to a role.
    :param list_of_names:
    :return:
    """
    return [Permission.get(code_name=name) for name in list_of_names]


def get_all_permissions(sort=False):
    if not sort:
        return Permission.select()
    else:
        return Permission.select().order_by(Permission.name)


def get_all_roles(sort=False):
    if not sort:
        return Role.select()
    else:
        return Role.select().order_by(Role.name)


@db_session
def get_role_from_id(role_id):
    if not role_id:
        return None
    return Role.get(id=role_id)


def get_role_from_name(target):
    try:
        return Role.get(name=target)
    except Exception as e:
        print(e)


@db_session
def get_authorized_pages_from_role_id(role_id):
    pages = [permission.code_name for permission in get_role_from_id(role_id).permissions]
    return pages


def get_role_name_from_id(role_id):
    return get_role_from_id(role_id).name


def get_all_role_types():
    return [(r, r) for r in ROLE_TYPE_IDS]


def get_user_role(role_id):
    return Role.get(id=role_id)


def get_all_role_permissions_code_names(role_id):
    return [permission.code_name for permission in get_role_from_id(role_id).permissions]
