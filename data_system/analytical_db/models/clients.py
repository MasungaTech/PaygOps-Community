from datetime import datetime
from pony.orm import select, group_concat, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from core_system.client.models import Client
from payg_loan_system.contracts.models.contract_status import ContractStatus
from shared.helpers.date_helper import age_from_birthdate
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


ENTERPRISE_FEATURES_ENABLED = getattr(config, "ENABLE_ENTERPRISE_FEATURES", False)


class Clients(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Clients are the actual people who have one or several contracts. This table contains the existing client and their information, not prospective clients (that are in the Leads table)'

    base_model = Client

    id = PrimaryKey(int, comment="The internal unique ID of the client")
    custom_id = Optional(str, comment="The custom identifier of the client, based on the Custom ID configuration (e.g. national ID card number, contract number from previous system, etc.)")
    first_name = Optional(str, comment="The first (given) name of the client")
    family_name = Optional(str, comment="The last (family) name of the client")
    birthdate = Optional(datetime, comment="The date of birth of the client")
    age = Optional(int, comment="The age of the client")
    gender = Optional(str, comment="The gender of the client")

    picture_uuid = Optional(str, comment="The unique ID of the picture of the client. The actual picture can be retreived using the API (see API documentation for more details)")
    language_sms = Optional(str, comment="The language used to send SMS to the client")
    language_spoken = Optional(str, comment="The language spoken by the client")
    longitude = Optional(float, comment="The longitude of the client as a WGS84 coordinate", precision=4)
    latitude = Optional(float, comment="The latitude of the client as a WGS84 coordinate", precision=4)

    primary_phone_number = Optional(str, comment="The primary phone number of the client")
    all_phone_numbers = Optional(str, "The comma-separated list of all phone numbers associated with the client")

    start_date = Optional(datetime, comment="The date at which the person became a client (start date of their first contract)")
    end_date = Optional(datetime, comment="The date at which the person stopped being a client (end date of their last contract)")

    has_active_contracts = Optional(bool, comment="True if the client has at least one active contract")
    has_completed_contracts = Optional(bool, comment="True if the client has at least one completed contract")
    has_defaulted_contracts = Optional(bool, comment="True if the client has at least one defaulted contract")
    has_late_contracts = Optional(bool, comment="True if the client has at least one late contract")


    client_group_id = Optional("Client_Groups", csv_columns=[("Client Group Name", lambda c: c.name)], comment="The ID of the client group to which the client belongs (if any)", column="client_group_id")
    l0_entity_id = Optional("Operational_Entities", csv_columns=[("L0 Entity Name", lambda c: c.name)], comment="The ID of the Level 0 entity to which the client belongs", column="l0_entity_id")
    l1_entity_id = Optional("Operational_Entities", csv_columns=[("L1 Entity Name", lambda c: c.name)], comment="The ID of the Level 1 parent of the L0 entity to which the client belongs", column="l1_entity_id")
    l2_entity_id = Optional("Operational_Entities", csv_columns=[("L2 Entity Name", lambda c: c.name)], comment="The ID of the Level 2 parent of the L0 entity to which the client belongs", column="l2_entity_id")
    l3_entity_id = Optional("Operational_Entities", csv_columns=[("L3 Entity Name", lambda c: c.name)], comment="The ID of the Level 3 parent of the L0 entity to which the client belongs", column="l3_entity_id")
    l4_entity_id = Optional("Operational_Entities", csv_columns=[("L4 Entity Name", lambda c: c.name)], comment="The ID of the Level 4 parent of the L0 entity to which the client belongs", column="l4_entity_id")

    note = Optional(str, comment="A free-form note about the client")
    tags = Optional(str, comment="The comma-separated list of tags associated with the client")

    overpaid_amount = Optional(float, comment="The total amount of overpaid payments of the client")

    user_in_charge_id = Optional("Users", comment="The Id of the user in charge of this client (inherited from L0 Entity and Client Group)", column="user_in_charge_id")

    # Virtual (not in the table)
    if ENTERPRISE_FEATURES_ENABLED:
        interactions = Set("Interactions")
        issues = Set("Issues")
        tasks = Set('Tasks')
    contract_repayments = Set("Contract_Payments")
    question_answers = Set("Question_Answers")
    contract_stats_historical = Set('Contracts_History')
    stock_items = Set('Stock_Items')
    origin_stock_movements = Set("Stock_Movements", reverse="origin_client_id")
    destination_stock_movements = Set("Stock_Movements", reverse="destination_client_id")
    contracts = Set("Contracts")
    leads = Set("Leads")
    reconciled_payments = Set("Reconciled_Payments")
    entity_changes = Set("L0_Entity_Changes")
    quantity_stock_items = Set('Quantity_Stock_Items')
    quantity_stock_movements_origin_client_id = Set('Quantity_Stock_Movements', reverse="origin_client_id")
    quantity_stock_movements_destination_client_id = Set('Quantity_Stock_Movements', reverse="destination_client_id")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @property
    def full_name(self):
        return f'{self.first_name} {self.family_name}'

    @staticmethod
    def converter(client):
        user_in_charge = client[19].user_in_charge if client[19] else client[15].inherited_user_in_charge
        return {
            "id": client[0],
            "custom_id": client[21] or '',
            "first_name": client[1],
            "family_name": client[2],
            "birthdate": client[3],
            "age": age_from_birthdate(client[3]) if client[3] else None,
            "gender": config.GENDER_NAMES.get(client[16], 'Unknown'),
            'picture_uuid': client[20].uuid if client[20] else '',
            "language_sms": config.LANGUAGES_NAMES.get(client[4], client[4]) if client[4] else '',
            "language_spoken": client[5] if client[5] else '',
            "longitude": client[6],
            "latitude": client[7],
            "start_date": client[8],
            "end_date": client[9],
            "note": client[10] if client[10] else '',
            "primary_phone_number": client[11].number if client[11] else '',
            "all_phone_numbers": client[12] if client[12] else "",
            "has_active_contracts": any(status == ContractStatus.active for status in [client[13]]),
            "has_completed_contracts": any(status == ContractStatus.completed for status in [client[13]]),
            "has_defaulted_contracts": any(status == ContractStatus.defaulted for status in [client[13]]),
            "has_late_contracts": any(status == ContractStatus.late for status in [client[13]]),
            "l0_entity_id": client[15].id,
            "l1_entity_id": client[15].l1_entity.id,
            "l2_entity_id": client[15].l2_entity.id,
            "l3_entity_id": client[15].l3_entity.id,
            "l4_entity_id": client[15].l4_entity.id,
            'tags': client[17] if client[17] else '',
            "client_group_id": client[19].id if client[19] else None,
            'last_updated': client[22],
            "overpaid_amount": client[23],
            "user_in_charge_id": user_in_charge.id
        }


    @staticmethod
    def selector(objects):
        return select((
            c.id,
            c.person.name,
            c.person.surname,
            c.person.birthdate,
            c.person.sms_language,
            c.person.verbal_language,
            c.person.GPSLon,
            c.person.GPSLat,
            min(contract.start_time for contract in c.contracts),
            max(contract.end_time for contract in c.contracts),
            c.Assets,
            c.person.contactPhone,
            group_concat(p.number for p in c.person.phoneNumbers),
            group_concat(contract.status for contract in c.contracts),
            group_concat(wallet.id for wallet in c.payment_wallets),
            c.person.village,
            c.person.gender,
            group_concat(tag.name for tag in c.tags),
            c,
            c.person.client_group,
            c.person.profile_picture,
            c.person.custom_id,
            Clients.extended_modified_date(c),
            sum(rp.amount for rp in c.person.reconciled_payments),
        ) for c in objects).order_by(23)

    @staticmethod
    def extended_modified_date(client):
        return max(
            client.modifiedDate,
            client.person.modifiedDate,
            max(c.modifiedDate for c in client.contracts),
            client.person.village.modifiedDate
        )
