from core_system.core_entities import db
from pony.orm import Optional, Required
from datetime import datetime
from core_system.operational_entities.models import Village

from sales_system.leads.models.lead import Lead


class PersonEntityChange(db.Entity):
    client = Optional("Client", column="client")
    lead = Optional(Lead, column="lead")
    date = Required(datetime, index=True)
    old_entity = Required(Village, column="old_entity")
    new_entity = Required(Village, column="new_entity")
    user = Required("User", column="user")

    @property
    def modifiedDate(self):
        return self.date