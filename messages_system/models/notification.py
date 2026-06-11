from flask import url_for
from datetime import datetime
from pony.orm import Required, Optional, Json
from core_system.core_entities import db


class Notification(db.Entity):
    text = Required(str)
    time = Required(datetime, default=datetime.now, index=True)
    operational_entity = Optional("HierarchicalOperationalEntity", column="operational_entity")
    endpoint = Optional(str)
    params = Optional(Json)
    url = Optional(str)

    @property
    def link(self):
        return url_for(self.endpoint, **self.params) if self.endpoint else self.url
