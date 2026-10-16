from pony.orm import db_session
from shared.migrations.migration_helper import add_column, drop_column, add_foreign_key_constraint, remove_foreign_key_column


@db_session
def up(db):
    add_column(db, 'stockmovement', 'quantity', 'int')

    add_column(db, 'stockmovement', 'product_sub_type', 'int')
    add_foreign_key_constraint(db, 'stockmovement', 'product_sub_type', 'productsubtype')

@db_session
def down(db):
    drop_column(db, 'stockmovement', 'quantity')
    remove_foreign_key_column(db, 'stockmovement', 'product_sub_type')