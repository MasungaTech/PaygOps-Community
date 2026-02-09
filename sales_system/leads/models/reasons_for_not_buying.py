from pony.orm import PrimaryKey, Required, Set
from core_system.core_entities import db


class ReasonsForNotBuying(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    leads = Set('Lead')
    status_changes = Set('StatusChangesHistory')