from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from core_system.operational_entities.models import ClientGroup
from datetime import datetime
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


class Client_Groups(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Groups of clients are used to organise a number of clients for operational purposes'

    base_model = ClientGroup

    id = PrimaryKey(int, comment="The internal unique ID of the client group")
    name = Optional(str, comment="The name of the client group")
    description = Optional(str, comment="The description of the client group")

    # Virtual (not in the table)
    leads = Set("Leads")
    clients = Set("Clients")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(group):
        return {
            "id": group[0],
            "name": group[1],
            "description": group[2] if group[2] else '',
            "last_updated": group[3]
        }

    @staticmethod
    def selector(objects):
        return select((
            p.id,
            p.name,
            p.description,
            Client_Groups.extended_modified_date(p)
        ) for p in objects).order_by(3)
