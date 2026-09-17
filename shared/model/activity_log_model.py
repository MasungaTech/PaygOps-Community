from datetime import datetime
from pony.orm import Required, Optional, Json
from core_system.core_entities import db
from shared.model.activity_log_db import audit_db


class OldActivityLogEntry(db.Entity):

    _table_ = 'activitylogentry' # This table should be removed later

    time = Required(datetime, index=True)
    user = Optional("User", column='user')
    ip = Required(str)
    path = Required(str)
    method = Required(str, index=True)
    args = Optional(Json)
    data = Optional(Json)
    app = Required(str)
    user_agent = Required(Json)


class ActivityLogEntry(audit_db.Entity):

    _table_ = 'activitylogentry'

    time = Required(datetime, index=True)
    user = Optional(int, index=True)
    ip = Required(str)
    path = Required(str)
    method = Required(str)
    args = Optional(Json, lazy=True)
    data = Optional(Json, lazy=True)
    app = Required(str)
    user_agent = Required(Json, lazy=True)
    

class AuditLogEntry(audit_db.Entity):

    time = Required(datetime, index=True)
    user_id = Optional(int, index=True)

    object_type = Optional(str, index=True)
    object_id = Optional(int, index=True)
    related_person_id = Optional(int, index=True)

    action = Optional(str, index=True)
    data = Optional(Json, lazy=True)

    platform = Optional(str, index=True)
    request_uuid = Optional(str, index=True) # Optional and sent by API from the person
    ip = Optional(str)
    user_agent = Optional(str)
    mocked_time = Optional(datetime)
