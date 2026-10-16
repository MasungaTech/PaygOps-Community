from pony.orm import db_session
from worker_app.tasks.update_analytical_db import update_analytical_db


@db_session
def up(db):
    update_analytical_db.delay(
        force_models=['Payments']
    )

@db_session
def down(db):
    pass
