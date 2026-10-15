from datetime import datetime
from pony.orm import select
from core_system.person.models.person_entity_change import PersonEntityChange
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


class L0_Entity_Changes(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'This table contains the history of the l0 entities of leads and clients, i.e. the movements of clients and leads from one l0 entity to another one. ' + \
        'Please consider than clients and leads that represents the same person are moved together, so in those cases there will be multiple rows (one per lead and client).'

    base_model = PersonEntityChange

    id = PrimaryKey(int, comment="The internal unique ID of the entity change")
    
    client_id = Optional('Clients', csv_columns=[("Client Name", lambda c: c.full_name)], comment="The internal ID of the client that was moved", column="client_id")
    lead_id = Optional('Leads', csv_columns=[("Lead Name", lambda l: l.full_name)], comment="The internal ID of the lead that was moved", column="lead_id")

    date = Optional(datetime, comment="The date of the entity change")

    old_l0_entity_id = Optional('Operational_Entities', csv_columns=[("Old L0 Entity Name", lambda c: c.name)], comment="The ID of the Level 0 entity before the change", column="old_l0_entity_id")
    new_l0_entity_id = Optional('Operational_Entities', csv_columns=[("New L0 Entity Name", lambda c: c.name)], comment="The ID of the Level 0 entity after the change", column="new_l0_entity_id")
    
    user_id = Optional('Users', comment="The ID of the user that did the change", column="user_id")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(ec):
        return {
            "id": ec.id,
            "lead_id": ec.lead.id if ec.lead else None,
            "client_id": ec.client.id if ec.client else None,
            "date": ec.date,
            "old_l0_entity_id": ec.old_entity.id,
            "new_l0_entity_id": ec.new_entity.id,
            "user_id": ec.user.id,
            'last_updated': L0_Entity_Changes.extended_modified_date(ec)
        }

    @staticmethod
    def selector(objects):
        return select(ec for ec in objects).order_by(1)
