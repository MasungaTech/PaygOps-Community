from pony.orm import db_session
from shared.model.billing import Bill
from shared.migrations.migration_helper import add_column_from_model_property, drop_column

@db_session
def up(db):
    add_column_from_model_property(Bill.extra_billing_info)

@db_session
def down(db):
    drop_column(db, 'bill', 'extra_billing_info')
