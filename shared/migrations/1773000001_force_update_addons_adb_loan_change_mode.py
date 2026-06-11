from pony.orm import db_session

from worker_app.tasks.update_analytical_db import update_analytical_db


@db_session
def up(adb):
    update_analytical_db.delay(
        force_models=['AddOns']
    )


@db_session
def down(adb):
    pass
