from pony.orm import db_session
from data_system.analytical_db.db import analytical_db
from shared.migrations.migration_helper import add_column, drop_column, add_foreign_key_constraint, remove_foreign_key_constraint


@db_session
def up(db):
    add_column(analytical_db, 'payments', 'back_payment_id', 'int')
    #add_foreign_key_constraint(analytical_db, 'payments', 'back_payment_id', 'payments')

@db_session
def down(db):
    #remove_foreign_key_constraint(analytical_db, 'payments', 'back_payment_id')
    drop_column(analytical_db, 'payments', 'back_payment_id')

