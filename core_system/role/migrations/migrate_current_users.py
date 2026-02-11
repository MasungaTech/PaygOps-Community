from core_system.users.models.user_model import User
from core_system.role.models import Role
from pony.orm import *
from core_system.role.permissions import LevelNames


@db_session
def update_user_auth_level():
    """
    Written by Andrew Graham-Yooll

    This migration is a bit tricky once the permission table is integrated into the main_db.
    What happens in that the table must be created in the main db for the permission system. When it does that
    the indexing and FK are created in the User table. When the integer is transferred from the sqlite file
    into postgres, the original integer is referencing the Role. But that is the WRONG role.

    For instance, the accountant role id is 10 in sqlite, but it might be something different in postgres db. This means
    you have to 'trick' the migration into thinking that the Role.id is the LevelName id.  Hence, that change.

    :return:
    """
    all_users = User.select()
    for user in all_users:
        auth_name = get_updated_auth_level_name(LevelNames[user.AuthorizationLevel.id])
        role_id = Role.get(name=auth_name)
        print(user.id, user.AuthorizationLevel.id, auth_name, role_id)
        user.AuthorizationLevel = role_id


def get_updated_auth_level_name(auth_name):
    update_auth_name_dict = {
        'LeadGenerator': 'ViewOnly',
        'SuperGuest': 'ViewOnly',
        'Retailer': 'ViewOnly',
        'Guest': 'ViewOnly',
        'Mentor': 'Agent'
    }

    if auth_name in update_auth_name_dict:
        return update_auth_name_dict[auth_name]
    else:
        return auth_name
