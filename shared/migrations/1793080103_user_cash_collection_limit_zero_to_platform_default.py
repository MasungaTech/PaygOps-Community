from pony.orm import db_session

from core_system.users.models.user_model import User


@db_session
def up(db):
    # A user limit of 0 used to fall back to the platform default, now it is an actual limit of 0
    db.execute(f'UPDATE "{User._table_}" SET cash_collection_limit = NULL WHERE cash_collection_limit = 0')


@db_session
def down(db):
    pass
