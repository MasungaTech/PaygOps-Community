from datetime import datetime
from sales_system.leads.services.lead_error_messages_service import Error
from sales_system.leads.models.status_category import StatusCategory
from pony.orm import Required, Optional, Set
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from core_system.core_entities import db


class LeadStatus(db.Entity):
    name = Required(str, unique=True)
    order = Required(int)
    color = Required(str, default="#000000")
    category = Required(str)
    leads = Set('Lead')
    status_changes_history = Set('StatusChangesHistory')

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = Optional(str, unique=True)

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    def before_update(self):
        self.modifiedDate = datetime.now()

    @classmethod
    def get_first(cls, category):
        return cls.select(lambda s: s.category == category).order_by(cls.order).first()

    def before_delete(self):
        if LeadStatus.select(lambda s: s.category == self.category).count() == 1:
            raise Exception('There must be at least one status per category')
