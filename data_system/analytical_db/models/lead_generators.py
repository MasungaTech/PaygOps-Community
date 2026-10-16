from calendar import c
from pony.orm import select, group_concat, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from sales_system.lead_generator.model import LeadGenerator
from datetime import datetime
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


class Lead_Generators(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Lead Generators are the source of the leads, the persons bringing new prospective clients. They can be users but can also be external to the company (e.g. clients, contractors, etc.)'

    base_model = LeadGenerator

    id = PrimaryKey(int, comment="The internal unique ID of the lead generator")
    first_name = Optional(str, comment="The first (given) name of the lead generator")
    family_name = Optional(str, comment="The last (family) name of the lead generator")
    primary_phone_number = Optional(str, comment="The primary phone number of the lead generator")
    all_phone_numbers = Optional(str, "The comma-separated list of all phone numbers associated with the lead generator")
    
    type = Optional(str, comment="The type of the lead generator (e.g. user, contractor, client, etc.)")
    start_date = Optional(datetime, comment="The date at which the person became a lead generator")
    active = Optional(bool, comment="True if the lead generator is active")

    entity_id = Optional("Operational_Entities", csv_columns=[("Entity Name", lambda l: l.name)], comment="The internal ID of the operational entity that the lead generator belongs to (if any)", column="entity_id")
    user_id = Optional("Users", reverse="lead_generator_id", comment="The internal ID of the user that the lead generator is linked to (if any)", column="user_id")

    # Virtual (not in table)
    leads = Set("Leads")
    contracts = Set("Contracts")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @property
    def full_name(self):
        return f'{self.first_name} {self.family_name}'

    @staticmethod
    def converter(lead_generator):
        return {
            "id": lead_generator[0],
            "first_name": lead_generator[1],
            "family_name": lead_generator[2],
            "primary_phone_number": lead_generator[3].number if lead_generator[3] else "",
            "all_phone_numbers": lead_generator[4] if lead_generator[4] else "",
            "start_date": lead_generator[7],
            "user_id": lead_generator[8].id if lead_generator[8] else None,
            "active": lead_generator[9],
            "type": lead_generator[5],
            "entity_id": lead_generator[8].shop.id if lead_generator[8] and lead_generator[8].shop else None,
            "last_updated": lead_generator[10]
        }

    @staticmethod
    def selector(objects):
        return select((
            l.id,
            l.person.name,
            l.person.surname,
            l.person.contactPhone,
            group_concat(p.number for p in l.person.phoneNumbers),
            l.type.name,
            l.person.village,
            l.start_date,
            l.person.user,
            l.working,
            Lead_Generators.extended_modified_date(l)
        ) for l in objects).order_by(11)

    @staticmethod
    def extended_modified_date(lg):
        return max(
            lg.modifiedDate,
            lg.person.modifiedDate
        )
