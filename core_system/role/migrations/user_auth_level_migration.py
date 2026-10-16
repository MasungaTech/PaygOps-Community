from core_system.users.models.user_model import User
from core_system.role.models import Role
from core_system.role.methods.getters import get_all_roles, get_role_from_name
from core_system.role.methods.setters import get_role_type, admin, mentors, managers, other, create_permission, \
    edit_role_from_form
from core_system.role.migrations.migrate_current_users import LevelNames
from pony.orm import *


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
        auth_name = LevelNames[user.AuthorizationLevel.id]
        role_id = Role.get(name=auth_name)
        print(user.id, user.AuthorizationLevel.id, auth_name, role_id)
        user.AuthorizationLevel = role_id


@db_session
def update_role_category():
    """
    Written by Andrew Graham-Yooll
    June 7, 2017

    This method was designed to update the role type codes in development.  It can be used in production,
    if a role type code needs to be added or altered.

    However, if it is to be used in production,
    the roles to be changed should be displayed in the setters.get_role_type() function.
    :return:
    """
    for role in get_all_roles():
        if role.name in admin + managers + other + mentors:
            update_type_code = get_role_type(role.name)
            if update_type_code is not role.type:
                role.type = update_type_code
                commit()


permissions_to_add = [{"name": 'Create Roles', 'code_name': 'CreateRoles', 'set_to': "SuperAdmin"}]


@db_session
def add_permissions_to_table():
    for permission in permissions_to_add:
        try:
            new_permission = create_permission(permission['name'], permission['code_name'])
            role = get_role_from_name(permission['set_to'])
            role.permissions += new_permission
            edit_role_from_form(role, role.name, role.type, role.permissions)
        except Exception as e:
            print(e)


@db_session
def alter_db_for_permissions_migration(db):
    try:
        # db.execute('CREATE TABLE "permission" ( \n'
        #            '"id" SERIAL PRIMARY KEY, \n'
        #            '"name" TEXT UNIQUE NOT NULL,\n'
        #            '"code_name" TEXT UNIQUE NOT NULL,\n'
        #            '"min_value" SMALLINT,\n'
        #            '"max_value" SMALLINT\n'
        #            ');\n')

        db.execute('CREATE TABLE "role" (\n'
                   ' "id" SERIAL PRIMARY KEY,\n'
                   ' "name" TEXT UNIQUE NOT NULL,\n'
                   ' "type" SMALLINT NOT NULL\n'
                   ');\n'
                   '\n')
        # db.execute('CREATE TABLE "permission_role" (\n'
        #            ' "permission" INTEGER NOT NULL,\n'
        #            ' "role" INTEGER NOT NULL,\n'
        #                        ' PRIMARY KEY ("permission", "role")\n'
        #            ');\n'
        # 'CREATE INDEX "idx_permission_role" ON "permission_role" ("role");\n'
        # db.execute('ALTER TABLE "permission_role" ADD CONSTRAINT "fk_permission_role__permission" FOREIGN KEY ("permission") REFERENCES "permission" ("id");\n'
        #            'ALTER TABLE "permission_role" ADD CONSTRAINT "fk_permission_role__role" FOREIGN KEY ("role") REFERENCES "role" ("id");\n'
        #            'CREATE INDEX "idx_user__role" ON "user" ("authorizationlevel");\n')
    except Exception as e:
        print(e)
        pass
