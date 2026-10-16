from pony.orm import db_session
from data_system.analytical_db.analytical_db import analytical_db
from shared.migrations.migration_helper import safe_add_colum, drop_column
from worker_app.tasks.update_analytical_db import update_analytical_db

@db_session
def up(db):
    safe_add_colum(analytical_db, 'tasks', 'status', 'text')
    update_analytical_db.delay(
        force_models=['Tasks']
    )

@db_session
def down(db):
    drop_column(analytical_db, 'tasks', 'status')

