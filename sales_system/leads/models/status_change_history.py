from datetime import datetime
from core_system.core_entities import db
from pony.orm import Required, Optional, Set


class StatusChangesHistory(db.Entity):
    lead = Required('Lead', column="lead")
    date = Required(datetime, index=True)
    status = Required(str)
    status_id = Optional('LeadStatus')
    next_contact = Optional(datetime)
    status_comment = Optional(str)
    reasons_for_not_buying = Set('ReasonsForNotBuying')

    _table_ = 'status_changes_history'

    @property
    def modifiedDate(self):
        return self.date
