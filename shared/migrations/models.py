from datetime import datetime
from pony.orm import db_session
from pony.orm.core import RowNotFound
from shared.migrations.migration_helper import add_column, create_table, drop_table


class DatabaseVersion:
    TABLE_NAME = 'database_version'

    @staticmethod
    @db_session
    def create_version_table(db,
                             table_name='database_version',
                             time_type='time'):
        try:
            create_table(db, table_name)
            add_column(db, table_name, 'updated_at', time_type, default=None, if_not_exists=False)
            add_column(db, table_name, 'version', 'int', default=None, if_not_exists=False)
            add_column(db, table_name, 'versions_executed', 'text', default=None, if_not_exists=False)
        except Exception as e:
            print(e)
            print('Database already exists.')

    @staticmethod
    @db_session
    def remove_version_table(db):
        try:
            drop_table(db, 'database_version')
        except Exception as e:
            print(e)
            print(db)
            print('Was not possible to drop database_version.')

    @staticmethod
    @db_session
    def latest_version(db):
        try:
            return db.get("select version from database_version limit 1")
        except RowNotFound:
            return 0

    @classmethod
    @db_session
    def set_version(cls, db, version):
        executed_migrations = cls.executed_migrations(db)
        if version not in executed_migrations:
            executed_migrations.append(version)
            cls.update_executed_migrations(db, executed_migrations)

        update_query = 'update database_version set '\
                       'version={}, updated_at=CURRENT_TIMESTAMP'\
                       ' where id = {}'

        create_query = 'insert into database_version '\
                       '(id, version, updated_at) values (1, {}, CURRENT_TIMESTAMP)'

        results = db.select("select id from database_version")

        if len(results) > 0:
            db.execute(update_query.format(version,
                                           results[0]))
        else:
            db.execute(create_query.format(version, datetime.today()))

    @staticmethod
    @db_session
    def executed_migrations(db):
        try:
            migrations = db.get("select versions_executed from database_version limit 1")
            return sorted([int(v) for v in migrations.split(',')])
        except Exception:
            return []

    @classmethod
    @db_session
    def is_pending(cls, db, version):
        migration_is_not_executed = version not in cls.executed_migrations(db)
        version_is_new = version > 100  # We check that its a timestamp and not an old migration

        return migration_is_not_executed and version_is_new

    @classmethod
    @db_session
    def update_executed_migrations(cls, db, executed_migrations):
        executed_migrations = [str(m) for m in executed_migrations]
        versions = ','.join(sorted(executed_migrations))

        try:
            rows = db.select("select id from database_version limit 1")
            db_version_id = rows[0]

            update_query = "update database_version set "\
                "versions_executed='{}' , updated_at=CURRENT_TIMESTAMP"\
                " where id = {}"

            db.execute(update_query.format(versions, db_version_id))
        except Exception as e:
            print('Was not possible to update {} - {}'.format(executed_migrations, str(e)))

    @classmethod
    @db_session
    def rollback_migration(cls, db, version):
        migrations = cls.executed_migrations(db)

        try:
            migrations.remove(version)
            cls.update_executed_migrations(db, migrations)
        except Exception as e:
            print('Was not possible to remove {} - {}'.format(version, e))

    @classmethod
    @db_session
    def update_latest_version(cls, db):
        executed_migrations = cls.executed_migrations(db)
        latest_version = 0

        if executed_migrations:
            latest_version = executed_migrations[-1]

        cls.set_version(db, latest_version)
