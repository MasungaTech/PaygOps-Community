from pony.orm import db_session

from worker_app.tasks.background_migrations_task import BackgroundMigrations


@db_session
def up(db):
    BackgroundMigrations.fix_phone_numbers()


@db_session
def down(db):
    pass
