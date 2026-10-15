from pony.orm import db_session

from data_system.analytical_db.analytical_db import analytical_db
from shared.migrations.migration_helper import drop_column, safe_add_colum
from worker_app.tasks.update_analytical_db import update_analytical_db


@db_session
def up(db):
    safe_add_colum(analytical_db, 'stock_items', 'addon_id', 'int')
    safe_add_colum(analytical_db, 'quantity_stock_items', 'addon_id', 'int')
    update_analytical_db.delay(
        force_models=['Stock_Items', 'Quantity_Stock_Items']
    )


@db_session
def down(db):
    drop_column(analytical_db, 'stock_items', 'addon_id')
    drop_column(analytical_db, 'quantity_stock_items', 'addon_id')
