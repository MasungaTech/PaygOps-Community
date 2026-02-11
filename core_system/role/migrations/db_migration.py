from pony.orm import *
from shared.migrations.migration_helper import setDBVersion

@db_session
def alter_db_for_permission_system_sqlite(db):
    try:
        db.execute('CREATE TABLE "Permission" ( \n'
                    '"id" INTEGER PRIMARY KEY AUTOINCREMENT,\n'
                    '"name" VARCHAR(30) UNIQUE NOT NULL,\n'
                    '"code_name" VARCHAR(30) UNIQUE NOT NULL,\n'
                    '"min_value" TINYINT,\n'
                    '"max_value" TINYINT \n'
                    ');\n')
    except Exception as e:
        print(e)
    try:
        db.execute('CREATE TABLE "Role" (\n'
                    '"id" INTEGER PRIMARY KEY AUTOINCREMENT,\n'
                    '"name" VARCHAR(30) UNIQUE NOT NULL,\n'
                    '"type" TINYINT NOT NULL\n'
                    ' );\n')
    except Exception as e:
        print(e)
    try:
        db.execute('CREATE TABLE "Permission_Role" (\n'
                    '"permission" INTEGER NOT NULL REFERENCES "Permission" ("id"),\n'
                    '"role" INTEGER NOT NULL REFERENCES "Role" ("id"),\n'
                    'PRIMARY KEY ("permission", "role")\n'
                    ');\n')
    except Exception as e:
        print(e)
    try:
        db.execute('CREATE INDEX "idx_permission_role" ON "Permission_Role" ("role");\n')
    except Exception as e:
        print(e)
    try:
        db.execute('CREATE INDEX "idx_user__role" ON "User"("authorizationlevel"); \n')
    except Exception as e:
        print(e)
    setDBVersion(db, 5)
