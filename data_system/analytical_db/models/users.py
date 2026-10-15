from datetime import datetime
from pony.orm import select, group_concat, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from core_system.users.models.user_model import User
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


ENTERPRISE_FEATURES_ENABLED = getattr(config, "ENABLE_ENTERPRISE_FEATURES", False)


class Users(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Users are the people who use the system. '

    base_model = User

    id = PrimaryKey(int, comment="The internal unique ID of the user")
    first_name = Optional(str, comment="The first (given) name of the user")
    family_name = Optional(str, comment="The last (family) name of the user")
    email = Optional(str, comment="The email address of the user")
    username = Optional(str, comment="The username of the user")
    role = Optional(str, comment="The role of the user (e.g. Field Agent, Accountant, etc.)")
    gender = Optional(str, comment='The user\'s gender')

    reference_entity_id = Optional("Operational_Entities", csv_columns=[("Reference Entity Name", lambda c: c.name)], reverse="users_referenced_entity", comment="The internal ID of the entity that the user is associated with", column="reference_entity_id")

    primary_phone_number = Optional(str, comment="The primary phone number of the user")
    all_phone_numbers = Optional(str, "The comma-separated list of all phone numbers associated with the user")

    last_web_access = Optional(datetime, comment="The date of the last connection of the user on the web app")
    last_mobile_sync = Optional(datetime, comment="The date of the last mobile app sync of the user")
    last_mobile_app_version = Optional(str, comment="The version of the mobile app the user was last seen using")

    expiration_date = Optional(datetime, comment="The date at which this user will become inactive")

    # Virtual (not in table)
    lead_generator_id = Optional("Lead_Generators")
    if ENTERPRISE_FEATURES_ENABLED:
        interactions = Set("Interactions")
        issues_created = Set("Issues")
        issues_assigned = Set("Issues")
        tasks_assignees = Set('Tasks', reverse='assignee_user_id')
        tasks_creators = Set('Tasks', reverse='creator_user_id')
    contract_events_approved = Set("Contract_Events")
    question_answers = Set("Question_Answers")
    add_ons_approved = Set("AddOns")
    add_ons_sold = Set("AddOns")
    stock_items = Set("Stock_Items")
    decided_leads = Set("Leads", reverse="decision_by_user_id")
    reconciled_payments = Set("Reconciled_Payments")
    origin_stock_movements = Set("Stock_Movements", reverse="origin_user_id")
    destination_stock_movements = Set("Stock_Movements", reverse="destination_user_id")
    entity_changed = Set("L0_Entity_Changes", reverse="user_id")
    leads_in_charge_of = Set("Leads", reverse="user_in_charge_id")
    clients_in_charge_of = Set("Clients", reverse="user_in_charge_id")
    approved_reversals = Set("Reversed_Payments", reverse="approver_id")
    quantity_stock_items = Set('Quantity_Stock_Items', reverse='with_user_id')
    quantity_stock_movements_origin_client_id = Set('Quantity_Stock_Movements', reverse="origin_user_id")
    quantity_stock_movements_destination_client_id = Set('Quantity_Stock_Movements', reverse="destination_user_id")
    
    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @property
    def full_name(self):
        return f'{self.first_name} {self.family_name}'

    @staticmethod
    def converter(user, reupdate=False):
        return {
            "id": user[0],
            "first_name": user[1],
            "family_name": user[2],
            "username": user[3],
            "role": user[4],
            "gender": config.GENDER_NAMES.get(user[11], ''), 
            "reference_entity_id": user[7].shop.id if user[7].shop and reupdate else None,
            
            "primary_phone_number": user[5].number if user[5] else '',
            "all_phone_numbers": user[6] if user[6] else '',
            
            "last_web_access": user[7].last_web_connection_time,
            "last_mobile_sync": user[7].last_mobile_connection_time,
            "last_mobile_app_version": user[7].last_mobile_app_version if user[7].last_mobile_app_version else '',
            
            "last_updated": user[8],
            "email": user[9] if user[9] else '',
            "expiration_date": user[10],
        }

    @staticmethod
    def selector(objects):
        return select((
            u.id,
            u.person.name,
            u.person.surname,
            u.username,
            u.AuthorizationLevel.name,
            u.person.contactPhone,
            group_concat(p.number for p in u.person.phoneNumbers),
            u,
            Users.extended_modified_date(u),
            u.email,
            u.loginExpirationDate,
            u.person.gender
        ) for u in objects).order_by(9)

    @staticmethod
    def extended_modified_date(user):
        return max(
            user.modifiedDate,
            user.person.modifiedDate,
            user.AuthorizationLevel.modifiedDate
        )
