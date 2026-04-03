from pony.orm import db_session
from shared.migrations.migration_helper import drop_column

@db_session
def up(db):
    drop_column(db, "user", "fcm_tokens")

@db_session
def down(db):
    # Note: If we need to rollback, we would need to add the column back
    # For now, we'll leave this empty as the column was removed from the model
    pass

