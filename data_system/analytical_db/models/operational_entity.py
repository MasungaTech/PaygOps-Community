from pony.orm import select, Set, desc
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from core_system.core_entities import db
from datetime import datetime
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


class Operational_Entities(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Operational Entities are used to organise the different physical locations within the area of operation of the organisation. They typically match the actual organisation of the company (e.g. Regional Office, District Office, Shop, Villages, etc.). Other objects (clients, leads, stock items, etc.) are associated with an Operational Entity.'

    base_model = db.HierarchicalOperationalEntity

    id = PrimaryKey(int, comment="The internal unique ID of the entity")
    name = Optional(str, comment="The name of the entity")
    level = Optional(int, comment="The level of the entity (e.g. 0 for a village, 1 for a shop, etc.)")
    user_in_charge = Optional(int, comment="The id of the user in charge")

    longitude = Optional(float, comment="The longitude of the entity as a WGS84 coordinate", precision=4)
    latitude = Optional(float, comment="The latitude of the entity as a WGS84 coordinate", precision=4)

    admin_contact_name = Optional(str, comment="The name of the administrative contact for the entity")
    admin_phone_number = Optional(str, comment="The phone number of the administrative contact for the entity")
    population = Optional(int, comment="The estimated population of the entity")

    description = Optional(str, comment="A free-form description of the entity")

    l0_entity_id = Optional("Operational_Entities", comment="The ID of the Level 0 entity to which the entity belongs (only present if level 0 itself)", column="l0_entity_id")
    l1_entity_id = Optional("Operational_Entities", csv_columns=[("L1 Entity Name", lambda c: c.name)], comment="The ID of the Level 1 entity to which the entity belongs", column="l1_entity_id")
    l2_entity_id = Optional("Operational_Entities", csv_columns=[("L2 Entity Name", lambda c: c.name)], comment="The ID of the Level 2 entity to which the entity belongs", column="l2_entity_id")
    l3_entity_id = Optional("Operational_Entities", csv_columns=[("L3 Entity Name", lambda c: c.name)], comment="The ID of the Level 3 entity to which the entity belongs", column="l3_entity_id")
    l4_entity_id = Optional("Operational_Entities", csv_columns=[("L4 Entity Name", lambda c: c.name)], comment="The ID of the Level 4 entity to which the entity belongs", column="l4_entity_id")

    # Virtual properties (not stored in the database)
    l0_clients = Set("Clients", reverse="l0_entity_id")
    l1_clients = Set("Clients", reverse="l1_entity_id")
    l2_clients = Set("Clients", reverse="l2_entity_id")
    l3_clients = Set("Clients", reverse="l3_entity_id")
    l4_clients = Set("Clients", reverse="l4_entity_id")
    l0_leads = Set("Leads", reverse="l0_entity_id")
    l1_leads = Set("Leads", reverse="l1_entity_id")
    l2_leads = Set("Leads", reverse="l2_entity_id")
    l3_leads = Set("Leads", reverse="l3_entity_id")
    l4_leads = Set("Leads", reverse="l4_entity_id")
    lead_generators = Set("Lead_Generators")
    stock_items = Set("Stock_Items")
    users_referenced_entity = Set("Users")
    l0_entities = Set("Operational_Entities", reverse="l0_entity_id")
    l1_entities = Set("Operational_Entities", reverse="l1_entity_id")
    l2_entities = Set("Operational_Entities", reverse="l2_entity_id")
    l3_entities = Set("Operational_Entities", reverse="l3_entity_id")
    l4_entities = Set("Operational_Entities", reverse="l4_entity_id")
    origin_stock_movements = Set("Stock_Movements", reverse="origin_entity_id")
    destination_stock_movements = Set("Stock_Movements", reverse="destination_entity_id")
    old_person_changes = Set("L0_Entity_Changes", reverse="old_l0_entity_id")
    new_person_changes = Set("L0_Entity_Changes", reverse="new_l0_entity_id")
    quantity_stock_items = Set('Quantity_Stock_Items', reverse='in_entity_id')
    quantity_stock_movements_origin_entity_id = Set('Quantity_Stock_Movements', reverse="origin_entity_id")
    quantity_stock_movements_destination_entity_id = Set('Quantity_Stock_Movements', reverse="destination_entity_id")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def selector(objects):
        # We sort by level so that previous levels are existing
        return select(entity for entity in objects).order_by(lambda o: desc(o.level))

    @staticmethod
    def converter(entity, reupdate=False):
        return {
            "id": entity.id,
            "name": entity.name,
            "level": entity.level,
            "user_in_charge": entity.user_in_charge.id if entity.user_in_charge else None,
            "latitude": entity.latitude,
            "longitude": entity.longitude,
            "admin_contact_name": entity.admin_contact_name or '',
            "admin_phone_number": entity.admin_phone_number or '',
            "population": entity.population,
            "description": entity.description or '',
            "l4_entity_id": entity.l4_entity.id if entity.l4_entity and reupdate else None,
            "l3_entity_id": entity.l3_entity.id if entity.l3_entity and reupdate else None,
            "l2_entity_id": entity.l2_entity.id if entity.l2_entity and reupdate else None,
            "l1_entity_id": entity.l1_entity.id if entity.l1_entity and reupdate else None,
            "l0_entity_id": entity.l0_entity.id if entity.l0_entity and reupdate else None,
            "last_updated": Operational_Entities.extended_modified_date(entity)
        }

