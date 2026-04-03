from pony.orm import db_session
from shared.migrations.migration_helper import column_required_to_optional, column_optional_to_required

@db_session
def up(db):
    column_required_to_optional(db, "offer", "family")

@db_session
def down(db):
    column_optional_to_required(db, "offer", "family")
