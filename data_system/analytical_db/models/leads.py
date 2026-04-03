from datetime import datetime
from pony.orm import select, group_concat, Set, coalesce
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from sales_system.leads.models.lead import Lead
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config
from decimal import Decimal


class Leads(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Leads contains the information about prospective sales. They can be linked to an existing client if the sale went through or if they want another contract (in which case several leads would be linked to that client). If they are not linked to a client it means that it would be their first contract.'

    base_model = Lead

    id = PrimaryKey(int, comment="The internal unique ID of the lead")
    custom_id = Optional(str, comment="The custom identifier of the lead, based on the Custom ID configuration (e.g. national ID card number, contract number from previous system, etc.)")
    first_name = Optional(str, comment="The first (given) name of the lead")
    family_name = Optional(str, comment="The last (family) name of the lead")
    birthdate = Optional(datetime, comment="The date of birth of the lead")
    age = Optional(int, comment="The age of the lead")
    gender = Optional(str, comment="The gender of the lead")

    picture_uuid = Optional(str, comment="The unique ID of the picture of the lead. The actual picture can be retreived using the API (see API documentation for more details)")
    language_sms = Optional(str, comment="The language used to send SMS to the lead")
    language_spoken = Optional(str, comment="The language spoken by the lead")
    longitude = Optional(float, comment="The longitude of the lead as a WGS84 coordinate", precision=4)
    latitude = Optional(float, comment="The latitude of the lead as a WGS84 coordinate", precision=4)

    primary_phone_number = Optional(str, comment="The primary phone number of the lead")
    all_phone_numbers = Optional(str, "The comma-separated list of all phone numbers associated with the lead")

    status = Optional(str, comment="The status of the lead (e.g. awaiting payment, completed, etc.)")
    status_category = Optional(str, comment="The status category of the lead (e.g. awaiting information, installed, etc.)")
    note = Optional(str, comment="A free-form note about the lead")
    reasons_for_not_buying = Optional(str, comment="A comma-separated list of the reasons why the lead did not buy the product")
    commission = Optional(Decimal, comment="The amount of the commission set on the lead (if any)")
    offer_id = Optional("Contract_Offers", csv_columns=[("Offer Name", lambda l: l.name)], comment="The internal ID of the offer of that lead", column="offer_id")

    lead_generator_id = Optional("Lead_Generators", csv_columns=[("Lead Generator Name", lambda l: l.full_name)], comment="The internal ID of the lead generator that generated the lead", column="lead_generator_id")
    entry_date = Optional(datetime, comment="The date at which the lead was entered into the system")
    generation_date = Optional(datetime, comment="The date at which the lead was generated")
    next_contact_date = Optional(datetime, comment="The date at which the next contact with the lead should be made")
    planned_delivery_date = Optional(datetime, comment="The date at which the lead should be delivered")
    last_status_change_date = Optional(datetime, comment="The date at which the status of the lead was last changed")
    decision_date = Optional(datetime, comment="The date at which the lead was approved or rejected (automatically or manually)")
    decision_by_user_id = Optional("Users", csv_columns=[("Decision User Name", lambda l: l.full_name)], comment="The internal ID of the user that approved or rejected the lead", column="decision_by_user_id")
    
    client_id = Optional("Clients", comment="The internal ID of the client that the lead is linked to", column="client_id")
    contract_reference = Optional(str, comment="The (future) reference of the contract that has/will come from the lead")

    portfolio_id = Optional("Portfolios", csv_columns=[("Portfolio Name", lambda c: c.name)], comment="The internal ID of the portfolio that the lead belongs to (if any)", column="portfolio_id")
    client_group_id = Optional("Client_Groups", csv_columns=[("Client Group Name", lambda c: c.name)], comment="The ID of the client group to which the lead belongs (if any)", column="client_group_id")
    l0_entity_id = Optional("Operational_Entities", csv_columns=[("L0 Entity Name", lambda c: c.name)], comment="The ID of the Level 0 entity to which the lead belongs", column="l0_entity_id")
    l1_entity_id = Optional("Operational_Entities", csv_columns=[("L1 Entity Name", lambda c: c.name)], comment="The ID of the Level 1 parent of the L0 entity to which the lead belongs", column="l1_entity_id")
    l2_entity_id = Optional("Operational_Entities", csv_columns=[("L2 Entity Name", lambda c: c.name)], comment="The ID of the Level 2 parent of the L0 entity to which the lead belongs", column="l2_entity_id")
    l3_entity_id = Optional("Operational_Entities", csv_columns=[("L3 Entity Name", lambda c: c.name)], comment="The ID of the Level 3 parent of the L0 entity to which the lead belongs", column="l3_entity_id")
    l4_entity_id = Optional("Operational_Entities", csv_columns=[("L4 Entity Name", lambda c: c.name)], comment="The ID of the Level 4 parent of the L0 entity to which the lead belongs", column="l4_entity_id")

    user_in_charge_id = Optional("Users", comment="The Id of the user in charge of this lead (inherited from L0 Entity and Client Group)", column="user_in_charge_id")

    # Virtual (not in table)
    reconciled_payments = Set("Reconciled_Payments")
    question_answers = Set("Question_Answers")
    contracts = Set("Contracts")
    addons = Set("AddOns")
    leads_history = Set("Leads_History")
    entity_changes = Set("L0_Entity_Changes")
    if config.ENABLE_ENTERPRISE_FEATURES:
        tasks = Set('Tasks')
    
    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)
    
    @property
    def full_name(self):
        return f'{self.first_name} {self.family_name}'

    @staticmethod
    def converter(lead, reupdate=False):
        birthdate = lead[3]
        user_in_charge = lead[25].user_in_charge.id if lead[25] else lead[16].inherited_user_in_charge.id
        result = {
            "id": lead[0],
            "custom_id": lead[28] or '',
            "first_name": lead[1],
            "family_name": lead[2],
            "birthdate": birthdate,
            "age": int((datetime.now() - birthdate).days/365) if birthdate is not None else None,
            "gender": config.GENDER_NAMES.get(lead[23], 'Unknown'),
            'picture_uuid': lead[24].uuid if lead[24] else '',
            "status": lead[4],
            "status_category": lead[31],
            "entry_date": lead[5],
            "generation_date": lead[26],
            "next_contact_date": lead[6],
            "decision_date": lead[7],
            "decision_by_user_id": lead[8].id if lead[8] else None,
            "note": lead[9] if lead[9] else "",
            "lead_generator_id": lead[10].id if lead[10] else None,
            "client_id": lead[11].id if lead[11] else None,
            "offer_id": lead[12].id if lead[12] else None,
            "contract_reference": lead[13] if lead[13] else "",
            "primary_phone_number": lead[14].number if lead[14] else '',
            "all_phone_numbers": lead[15] if lead[15] else "",
            "l0_entity_id": lead[16].id if lead[16] else None,
            "l1_entity_id": lead[16].l1_entity.id if lead[16] else None,
            "l2_entity_id": lead[16].l2_entity.id if lead[16] else None,
            "l3_entity_id": lead[16].l3_entity.id if lead[16] else None,
            "l4_entity_id": lead[16].l4_entity.id if lead[16] else None,
            "reasons_for_not_buying": lead[18] if lead[18] else "",
            'planned_delivery_date': lead[19],
            'longitude': lead[20],
            'latitude': lead[21],
            'last_status_change_date': lead[22],
            "client_group_id": lead[25].id if lead[25] else None,
            "portfolio_id": lead[17].id if lead[17] else None,
            "commission": lead[27],
            "language_sms": config.LANGUAGES_NAMES.get(lead[29], lead[29]) if lead[29] else '',
            "language_spoken": lead[30] if lead[30] else '',
            'last_updated': lead[32],
            'user_in_charge_id': user_in_charge
        }
        return result

    @staticmethod
    def selector(objects):
        generator = ((
            l.id,
            l.person.name,
            l.person.surname,
            l.person.birthdate,
            l.status.name,
            l.entryDate,
            l.nextContact,
            l.decisionTime,
            l.decisionMaker,
            l.status_comment,
            l.generator,
            l.person.client,
            l.offer,
            l.future_contract_reference,
            l.person.contactPhone,
            group_concat(p.number for p in l.person.phoneNumbers),
            l.person.village,
            l.portfolio,
            group_concat(r.name for r in l.reasons_for_not_buying),
            l.agreedDeliveryDate,
            l.person.GPSLon,
            l.person.GPSLat,
            l.statusUpdate,
            l.person.gender,
            l.person.profile_picture,
            l.person.client_group,
            l.receptionTime,
            l.commission,
            l.person.custom_id,
            l.person.sms_language,
            l.person.verbal_language,
            l.status.category,
            Leads.extended_modified_date(l)
        ) for l in objects)
        return select(generator).order_by(33)

    @staticmethod
    def extended_modified_date(lead):
        return max(
            lead.modifiedDate, 
            lead.person.modifiedDate, 
            lead.person.village.modifiedDate,
            lead.person.village.l1_entity.modifiedDate,
            lead.person.village.l2_entity.modifiedDate,
            lead.person.village.l3_entity.modifiedDate,
            lead.person.village.l4_entity.modifiedDate,
        )
