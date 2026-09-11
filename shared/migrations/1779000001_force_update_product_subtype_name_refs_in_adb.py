from pony.orm import db_session

from worker_app.tasks.update_analytical_db import update_analytical_db


@db_session
def up(adb):
    update_analytical_db.delay(
        force_models=[
            'Product_SubTypes',
            'Stock_Items',
            'Stock_Movements',
            'Quantity_Stock_Items',
            'Quantity_Stock_Movements',
        ]
    )


@db_session
def down(adb):
    pass
