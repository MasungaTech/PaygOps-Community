from datetime import datetime
from pony.orm import Required, Json
from core_system.core_entities import db


class CommunicationCampaign(db.Entity):
    time = Required(datetime)
    name = Required(str)
    user = Required("User", column="user")
    content = Required(str)
    stats = Required(Json)
    criteria = Required(Json)
    messages = Required(Json)
