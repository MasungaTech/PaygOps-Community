from pony.orm import db_session
from shared.migrations.migration_helper import add_column, drop_column

@db_session
def up(db):
    add_column(db, "task", "started_time", "datetime")

@db_session
def down(db):
    drop_column(db, "task", "started_time")

