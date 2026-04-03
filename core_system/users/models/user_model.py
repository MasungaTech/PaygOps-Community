from datetime import datetime, timedelta
from decimal import Decimal

from flask import has_request_context, request, url_for
from flask_login import logout_user
from pony.orm import Json, Optional, Required, Set, StrArray, db_session, desc, select

import config
from accounting_system.accounting_db import accounting_db
from constants import (BOOLEAN_PATTERN, FEATURE_FLAGS_CONFIG,
                       OPTIONAL_DATETIME_OPTIONS, OPTIONAL_EMAIL_OPTIONS,
                       REQUIRED_STRING_PATTERN)
from core_system.core_entities import db
from core_system.operational_entities.models import (
    HierarchicalOperationalEntity, OperationalEntity,
    UserWithRole)
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from core_system.operational_entities.services.operational_entities_helper import \
    OperationalEntitiesHelper
from core_system.role.methods.getters import (get_all_permissions,
                                              get_role_from_name,
                                              get_role_name_from_id,
                                              get_user_role)
from core_system.role.models import Permission, Role
from core_system.role.permissions import (global_permissions,
                                          synthetic_permissions)
from messages_system.models.communications import CommunicationCampaign
from payg_loan_system.payments.models.wallet import (PaymentWalletOwner,
                                                     PaymentWalletType)
from payg_loan_system.reversed_payments.models import ReversedPayment
from payg_loan_system.transaction_requests.models import TransactionRequest
from shared.api_helpers.client_helpers.uuid_generation_helpers import \
    generate_uuid
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.api_helpers.server_helpers.jwt_generation import \
    generate_jwt_for_user
from shared.logger.loggers import Error, LogAPI
from shared.model.interface import ModelInterface
from shared.services.settings_service import SettingsService
import config

if config.ENABLE_ENTERPRISE_FEATURES:
    from app_builder_system.user_journey_editor.models.models import UserJourneyRunStep
    from app_builder_system.automations.models.automation_model import Automation
else:
    UserJourneyRunStep = None
    Automation = None
from tests.support.mock_query import MockQuery

class User(db.Entity, ModelInterface, ModelDefinitionMixin):

    person = Required('Person', column="person")

    AuthorizationLevel = Required("Role", column="authorizationlevel")
    email = Optional(str, nullable=True)
    username = Required(str, unique=True)
    password = Required(str)
    pin = Optional(str)
    loginExpirationDate = Optional(datetime, volatile=True)
    organization = Optional(str)
    shop = Optional(HierarchicalOperationalEntity, reverse="reference_of_users", column="reference_entity")

    mentorID = Optional(int, unique=True) # TO DO: remove
    accountingUserID = Optional(int, unique=True)

    reported = Set('Lead', reverse='reporter', cascade_delete=False)
    decided = Set('Lead', reverse='decisionMaker', cascade_delete=False)
    managed_operational_entities = Set("OperationalEntity", cascade_delete=False)
    roles_in_entities = Set("UserWithRole", cascade_delete=True)
    updatedQuestions = Set('Question', reverse='updatedBy', cascade_delete=False)
    updatedSurveys = Set('FormVersion', reverse='updatedBy', cascade_delete=False)
    # Interaction reports and issues are enterprise-only concepts. In OSS mode,
    # we still keep the reverse FK column mapped as integers to avoid requiring
    # the InteractionReport/Issue entities to exist.
    if getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False):
        interactionReports = Set('InteractionReport', cascade_delete=False)
        updatedIssues = Set('Issue', reverse='updateBy', cascade_delete=False)
        createdIssues = Set('Issue', reverse='creator', cascade_delete=False)
        assignedIssues = Set('Issue', reverse='assignee', cascade_delete=False)
    transaction_requests = Set(TransactionRequest, cascade_delete=False)
    # Device/customer notes are enterprise-only; keep FK as int in OSS mode.
    if getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False):
        notes = Set('Note', cascade_delete=False)
    contract_events_approved = Set('ContractEvent', cascade_delete=False)
    add_ons_approved = Set('ContractAddOn', cascade_delete=False)
    add_ons_sold = Set('ContractAddOn', cascade_delete=False)
    add_ons_canceled = Set('ContractAddOn', cascade_delete=False)
    communication_campaigns = Set(CommunicationCampaign, cascade_delete=False)
    payment_wallets = Set('PaymentWallet', cascade_delete=False)

    activity_log = Set('OldActivityLogEntry', cascade_delete=True)

    last_web_connection_time = Optional(datetime, volatile=True)
    last_mobile_connection_time = Optional(datetime, volatile=True)
    last_mobile_app_version = Optional(str, volatile=True)
    last_mobile_app_sync_report = Optional(Json, lazy=True)
    last_bad_login_time = Optional(datetime)
    bad_login_count = Required(int, default=0)
    last_notifications_time = Optional(datetime)
    show_notifications = Required(bool, default=True)
    cash_collection_limit = Optional(Decimal)

    # Two-factor authentication fields
    two_factor_enabled = Required(bool, default=False)
    two_factor_secret = Optional(str)
    two_factor_setup_time = Optional(datetime)
    backup_codes = Optional(Json, lazy=True)  # List of hashed backup codes

    stock_movements = Set('StockMovement')
    destined_stock = Set('StockMovement')
    approved_wallet_owners = Set("PaymentWalletOwner")
    owned_wallets = Set("PaymentWalletOwner")
    mentor_requests = Set('MentorRequest')
    handled_reversals = Set(ReversedPayment)
    reconciled_payments = Set('ReconciledPayment')
    person_entity_changes = Set('PersonEntityChange')
    webhooks_created = Set('Webhook')
    device_notes = Set('DeviceNote')
    quantity_stock_locations = Set('QuantityStockLocation')
    quantity_stock_movements = Set('QuantityStockMovement')
    if config.ENABLE_ENTERPRISE_FEATURES and UserJourneyRunStep:
        user_journey_run_steps = Set(UserJourneyRunStep)
        tasks_assignees = Set('Task', reverse='assignee')
        tasks_creators = Set('Task', reverse='creator')
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = Optional(str, unique=True)
    api_access_only = Optional(bool, default=False)
    if config.ENABLE_ENTERPRISE_FEATURES:
        automations_created = Set('Automation', cascade_delete=False)

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    def get_display_id(self):
        return str(self.id)

    def before_delete(self):
        if 'admin@test.com' == self.username:
            raise Exception('user '+ self.username)

    def before_update(self):
        self.modifiedDate = datetime.now()

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "description": "This is the ID of the User",
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id
                },
                'name': {
                    "description": "The name of the User",
                    "type": "string",
                    "pattern": REQUIRED_STRING_PATTERN,
                    "example": "Name",
                    "value": lambda o: o.person.name
                },
                'surname': {
                    "description": "The surname(s) of the User",
                    "type": "string",
                    "pattern": REQUIRED_STRING_PATTERN,
                    "example": "Surname",
                    "value": lambda o: o.person.surname
                },
                'birthdate': {
                    "description": "This is the date and time at which the person was born, in ISO 8601 format.",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime(1980, 6, 15).isoformat(),
                    "value": lambda o: o.person.birthdate
                },
                'gender': {
                    "description": "This is the person's gender.",
                    "type": "string",
                    "example": list(config.GENDER_NAMES.values())[0],
                    "value": lambda o: o.person.get_gender_name(lower=True) or None
                },
                'email': {
                    "description": "The user email that will be used for login and password recovery",
                    "type": "string",
                    "oneOf": OPTIONAL_EMAIL_OPTIONS,
                    "example": "user@domain.com",
                    "value": lambda o: o.email
                },
                'username': {
                    "description": "The username that will be used for login and password recovery",
                    "type": "string",
                    "pattern": REQUIRED_STRING_PATTERN,
                    "example": "user@domain.com",
                    "value": lambda o: o.username
                },
                'password': {
                    "description": "The SHA256 hash of the actual password string",
                    "type": "string",
                    "format": "password",
                    "example": "b6bc7b58510319a151d168ba3d5aecb3ac0a9708d06dd930f37fbc89b6cdc697",
                },
                'password_confirm': {
                    "description": "The SHA256 hash of the actual password string, for confirmation",
                    "type": "string",
                    "format": "password",
                    "example": "b6bc7b58510319a151d168ba3d5aecb3ac0a9708d06dd930f37fbc89b6cdc697",
                },
                'auto_generate_password': {
                    "description": "Autogenerate password and send it by email. Defaults to `true` if no password is provided. ",
                    "type": "boolean",
                    "pattern": BOOLEAN_PATTERN,
                    "example": True,
                },
                'mobile_pin': {
                    "description": "The numbers used as Mobile App PIN",
                    "type": "number",
                    "example": 1234,
                },
                'bad_login_count': {
                    "description": "The number of unsuccessful login attempts",
                    "type": "number",
                    "example": 2,
                    "value": lambda o: o.bad_login_count
                },
                'cash_collection_limit': {
                    "description": "The limit of cash that the user can collect (empty means the platform default)",
                    "type": "number",
                    "example": 30000,
                    "value": lambda o: o.cash_collection_limit
                },
                'role_id': {
                    "description": "The ID of the role of the user.",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.AuthorizationLevel.id
                },
                'hub_id': {
                    "description": "The old ID of the hub of the user",
                    "type": "integer",
                    "example": 12,
                    "deprecated": True,
                    "value": lambda o: o.shop.not_empty_code if o.shop else None
                },
                'reference_entity_id': {
                    "description": "The ID of the reference entity of the user",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.shop.id if o.shop else None
                },
                'login_expiration_date': {
                    "description": "This is the date when the user will stop being able to use the account. Null if the account should be available forever. ",
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.loginExpirationDate
                },
                'phone_number': {
                    "description": "The preferred phone number with the extension or null if no one is provided",
                    "type": "string",
                    "format": "phone",
                    "example": "+25512341234",
                    "value": lambda o: getattr(o.person.contactPhone, 'number', ''),
                    "deprecated": True
                },
                'phone_numbers': {
                    "type": "array",
                    "description": "The phone numbers associated with the client (including the contact phone number)",
                    "items": {
                        "type": "string",
                        "format": "phone"
                    },
                    "example": ["+25534534545", "+25534534546"],
                    "value": lambda o: [p.number for p in o.person.phoneNumbers]
                },
                'preferred_phone_number': {
                    "description": "The preferred phone number with the extension or null if no one is provided",
                    "type": "string",
                    "format": "phone",
                    "example": "+25512341234",
                    "value": lambda o: getattr(o.person.contactPhone, 'number', '')
                },
                'language': {
                    "description": "The code of the language to be used in the platform or in SMS messages to the user. ",
                    "type": "string",
                    "enum": ["FR","EN"],
                    "example": "FR",
                    "value": lambda o: o.person.sms_language
                },
                'sms_language': {
                    "description": "The language code among the available ones to be used in the SMS communication or an empty string if not provided",
                    "type": "string",
                    "example": "FR",
                    "value": lambda o: o.person.sms_language,
                    "deprecated": True
                },
                'verbal_language': {
                    "description": "Text containing additional information about the preferred language for verbal communication with the lead. It can be any string or an empty string if not provided",
                    "type": "string",
                    "example": "Local Language",
                    "value": lambda o: o.person.verbal_language,
                    "deprecated": True
                },
                'last_web_connection_time': {
                    "description": "This is the last time the user used the web app. Null if never used.",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.last_web_connection_time
                },
                'last_mobile_connection_time': {
                    "description": "This is the last time the user logged in or synced on mobile. Null if never used. ",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.last_mobile_connection_time
                },
                'last_mobile_app_version': {
                    "description": "This is the mobile app version used the last time the user synced on mobile app. Null if never used. ",
                    "type": "string",
                    "example": config.mobile_app_version,
                    "value": lambda o: o.last_mobile_app_version or None
                },
                'preferred_password_communication': {
                    "type": "string",
                    "example": "email",
                    "enum": ['email', 'sms'],
                    "value": lambda o: o.preferred_password_communication,
                    "description": "This is the method of communication to be used when sending the password."
                },
                'organization': {
                    "description": "This is the mobile app version used the last time the user synced on mobile app. Null if never used. ",
                    "type": "string",
                    "example": 'Internal',
                    "value": lambda o: o.organization if o.organization else None
                },
                'lead_generator_type': {
                    "description": "The type of lead generator",
                    "type": "string",
                    "example": "Sales Leader",
                    "value": lambda o: o.person.leadGenerator.type.name if o.person.leadGenerator else None
                },
                'lead_generator_id': {
                    "description": "The ID of the lead generator",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.person.leadGenerator.id if o.person.leadGenerator else None
                },
                'api_access_only': { 
                    "description": "The status of restriction to API documention only",
                    "type": "boolean",
                    "example": True
                }    
            },
            "create_required": ["name", "surname", "username", "role_id", "reference_entity_id"],
            "create_allowed": ["preferred_phone_number", "phone_numbers", "phone_number", "login_expiration_date", "reference_entity_id", "hub_id", "role_id", "auto_generate_password", "password", "password_confirm", "mobile_pin", "email", "username", "name", "surname", "birthdate", "gender", "sms_language", "verbal_language", "language", "cash_collection_limit", "organization", "lead_generator_type", "api_access_only"],
            "edit_required": [],
            "edit_allowed": ["preferred_phone_number", "phone_numbers", "phone_number", "login_expiration_date", "reference_entity_id", "hub_id", "role_id", "auto_generate_password", "password", "password_confirm", "mobile_pin", "email", "name", "surname", "birthdate", "gender", "sms_language", "verbal_language", "language", "username", "cash_collection_limit", "bad_login_count", "organization", "api_access_only"],
            "view_required": [],
            "view_forbidden": ["api_access_only", "password", "password_confirm", "mobile_pin", "preferred_password_communication", "auto_generate_password", "bad_login_count"],
            "view_allowed": []
        }

    @property
    def full_name(self):
        return self.person.full_name
    
    @property
    def full_name_and_id(self):
        return "%s (ID: %d)" % (self.person.full_name, self.id)
    
    @property
    def banned_time(self):
        BLOCKING_COUNT = 5
        if self.bad_login_count > BLOCKING_COUNT:
            if not self.last_bad_login_time:
                self.last_bad_login_time = datetime.now()
            banned_until = self.last_bad_login_time + timedelta(minutes=min((self.bad_login_count-BLOCKING_COUNT)**2, 256))
            remaining = banned_until-datetime.now()
            return remaining if remaining > timedelta() else None
        return None
        
    @property
    def total_reconciled(self):
        return select(r.amount for r in self.reconciled_payments).sum()

    @property
    def cash_limit_overall(self):
        return self.cash_collection_limit or SettingsService.get_setting('CashCollectionLimit') \
            if SettingsService.get_setting('CashCollectionLimitEnabled') else None

    @property
    def total_cash_collected(self):
        return self.get_cash_account().get_balance()

    @property
    def cash_allowance(self):
        return self.cash_limit_overall - self.total_cash_collected + self.total_reconciled if self.cash_limit_overall else None

    @property
    def active(self):
        return self.loginExpirationDate is None or self.loginExpirationDate > datetime.now()
    
    @property
    def mobile_money_wallets(self):
        return self.payment_wallets.filter(lambda w: w.Type == PaymentWalletType.mobile_money)

    def update_last_web_connection(self):
        now = datetime.now()
        if not self.last_web_connection_time or (self.last_web_connection_time + timedelta(minutes=15) < now):
            self.last_web_connection_time = now

    def update_last_mobile_connection(self):
        now = datetime.now()
        if not self.last_mobile_connection_time or (self.last_mobile_connection_time + timedelta(minutes=15) < now):
            self.last_mobile_connection_time = now
    
    def can_access_in_scope(self, permission, in_all=False):
        if isinstance(permission, list):
            return any(self.can_access_in_scope(p) for p in permission)
        assert not isinstance(permission, list)
        return self.can_access(permission) if permission in global_permissions else (self.can_access_in_all(permission) if in_all else self.can_access_in_any(permission))
    
    def can_access_modular(self, permission, person=None, entity=None):
        if not person and not entity:
            return self.can_access_in_scope(permission)
        else:
            return self.can_access(permission, person=person, entity=entity)
    
    def check_access(self, permission, entity=None, person=None, check_special=True):
        '''
        Same as can_access but raises the corresponding error if not allowed.
        '''
        if not self.can_access(permission, entity=entity, person=person, check_special=check_special):
            raise Error('INSUFFICIENT_PERMISSION', permission=permission)

    def can_access(self, permission, entity=None, person=None, check_special=True):
        if self.not_enabled_in_features_config(permission):
            return False
        if self.api_access_only and permission != 'ViewAPIDocumentation':
            return False

        if person:
            if check_special:
                # We check that if the user can viewcreated or viewgenerated and has in default role he can
                if person.user_has_special_permission(self) and (permission in [p.code_name for p in self.AuthorizationLevel.permissions]):
                    return True
            if person.client_group:
                return self.can_access(permission, entity=person.client_group) or self.can_access(permission, entity=person.village)
            if person.user:
                entity = person.user.shop
            elif person.village:
                entity = person.village
            elif person.leadGenerator:
                if isinstance(permission, list):
                    return not permission or any([self.can_access_in_any(p) for p in permission])
                return self.can_access_in_any(permission)
            else:
                raise Exception("Couldn't find an entity for the person")
        self = self.reload()
        if not isinstance(permission, list) and synthetic_permissions.get(permission):
            permission = synthetic_permissions[permission]
        if isinstance(permission, list):
            if not permission:
                return True
            for p in permission:
                if self.can_access(p, entity=entity, person=person):
                    return True
            return False
        if permission == 'SuperAdmin':
            if self.is_super_admin():
                return True
        else:
            LogAPI.check_and_warn(permission in [p.code_name for p in get_all_permissions()], f"Permission {permission} was checked but is not defined in the system")
        
        if self.is_expired():
            return False
        if permission not in global_permissions:
            if entity:
                return self.can_access_in_all(permission) or entity in self.get_entities_with_permission(permission)
            if not config.MIGRATE_MODE:
                msg = f'{permission} checked in default role but declared as local permission'
                if config.ENV_VAR == 'TEST' or config.ENV_VAR == 'DEV':
                    raise Exception(msg)
                LogAPI.Warning(msg)
        # This is a request level cache to avoid querying the permissions many times in a pageload for a user
        if has_request_context():
            pkey = 'user_permissions_'+str(getattr(self, 'id', 'noid'))
            perms = request.environ.get(pkey)
            if not perms:
                perms = [p.code_name for p in self.AuthorizationLevel.permissions]
                request.environ[pkey] = perms
        else:
            perms = [p.code_name for p in self.AuthorizationLevel.permissions]
        return permission in perms

    def reload(self):
        return User.get(id=self.id)
    
    @classmethod
    def get_system_user(cls):
        return cls.get(username=config.SYSTEM_EMAIL)

    def is_expired(self):
        if self.loginExpirationDate is not None and self.loginExpirationDate < datetime.now():
            return True
        else:
            return False

    def is_admin(self):
        return self.get_role().type == 3

    def is_super_admin(self):
        return self.get_role() == get_role_from_name('SuperAdmin')

    def get_accessible_permissions(self, entity=None):
        role_id = self.AuthorizationLevel.id
        if entity:
            role_id = getattr(UserWithRole.get(entity=entity, user=self), "id", None)
            if not role_id:
                raise Error('User has no role assigned in that entity')
        roles_in_entities = select(rie.role for rie in self.roles_in_entities)
        roles = Role.select(lambda r: r in roles_in_entities or r == self.AuthorizationLevel)
        permissions = select(r.permissions for r in roles)
        return [p.code_name for p in permissions]

    def get_client_groups(self):
        return self.roles_in_entities.filter(lambda rie: rie.entity.level == -1)

    def get_max_visible_level(self):
        can_see_all = self.roles_in_entities.filter(lambda rie: rie.entity == None).count() > 0
        user_max = select(rie.entity.level for rie in self.roles_in_entities).max() or 0
        global_max = OperationalEntitiesHelper.get_max_level_enabled()
        if not can_see_all and user_max < global_max:
            return user_max
        return global_max
    
    def get_roles_in_entities_for_permission(self, permission_code, for_sync=False, for_api_docs=False):
        if self.api_access_only and not for_api_docs:
            return self.roles_in_entities.filter(lambda rie: rie.id == -1)
        if not isinstance(permission_code, list) and synthetic_permissions.get(permission_code):
            permissions = synthetic_permissions[permission_code]
            forbidden = self.roles_in_entities
            for permission in permissions:
                allowed = self.get_roles_in_entities_for_permission(permission, for_sync=False)
                forbidden = forbidden.filter(lambda rie: rie not in allowed)
            return self.roles_in_entities.filter(lambda rie: rie not in forbidden)
        permission = Permission.get(code_name=permission_code)
        if not permission:
            raise Error(f'Permission {permission_code} not found')
        allowed_roles_in_entites = self.roles_in_entities.filter(lambda rie: not rie.role or permission in rie.role.permissions)
        if not permission in self.reload().AuthorizationLevel.permissions:
            allowed_roles_in_entites = allowed_roles_in_entites.filter(lambda rie: rie.role is not None)
        if for_sync:
            allowed_roles_in_entites = allowed_roles_in_entites.filter(lambda rie: rie.sync_entity)
        return allowed_roles_in_entites

    def can_access_in_entities(self, permission_code, entities):
        return any(self.can_access(permission_code, entity) for entity in entities)

    def can_access_in_all(self, permission_code):
        if isinstance(permission_code, list):
            return any(self.can_access_in_all(p) for p in permission_code)
        if synthetic_permissions.get(permission_code):
            return any(self.can_access_in_all(p) for p in synthetic_permissions[permission_code])
        if self.not_enabled_in_features_config(permission_code):
            return False
        if permission_code == 'SuperAdmin':
            return self.is_super_admin()
        return self.get_roles_in_entities_for_permission(permission_code).filter(entity=None).exists()

    def can_access_in_any(self, permission_code, for_api_docs=False):
        if isinstance(permission_code, list):
            return any(self.can_access_in_any(p, for_api_docs=for_api_docs) for p in permission_code)
        if synthetic_permissions.get(permission_code):
            return any(self.can_access_in_any(p, for_api_docs=for_api_docs) for p in synthetic_permissions[permission_code])
        if self.not_enabled_in_features_config(permission_code):
            return False
        if permission_code == 'SuperAdmin':
            return self.is_super_admin()
        return self.get_roles_in_entities_for_permission(permission_code, for_api_docs=for_api_docs).exists()

    def _filter_managed_by(self, entities, managed_by=None):
        if managed_by:
            entities = entities.filter(lambda oe: oe.user_in_charge == managed_by)
        return entities 
    
    def get_entities_with_permission(self, permission_code, level=None, for_sync=False, managed_by=None):
        if self.can_access_in_all(permission_code) and not for_sync:
            if level is None:
                entities = OperationalEntity.select()
            else:
                entities = OperationalEntity.select(lambda oe: oe.level == level)
            entities = self._filter_managed_by(entities, managed_by)
            return entities
        else:
            allowed_roles_in_entites = self.get_roles_in_entities_for_permission(permission_code, for_sync=for_sync)
            entities = select(rie.entity for rie in allowed_roles_in_entites if rie.entity)
            if not entities:
                return entities
            entities = self._filter_managed_by(entities, managed_by)
            all_entities = OperationalEntitiesGetterService.all_descendents_from_entites(entities)
            return all_entities.filter(lambda e: e.level == level) if level else all_entities

    def get_client_group_with_permission(self, permission_code, for_sync=False, managed_by=None):
        allowed_roles_in_entites = self.get_roles_in_entities_for_permission(permission_code, for_sync=for_sync)
        entities = select(rie.entity for rie in allowed_roles_in_entites if rie.entity and rie.entity.level == -1)
        entities = self._filter_managed_by(entities, managed_by)
        return entities

    def get_villages_and_client_groups_with_permission(self, permission_code, for_sync=False, return_cg_ids=True, return_villages_ids=False, managed_by=None):   
        villages = self.get_entities_with_permission(permission_code, level=0, for_sync=for_sync, managed_by=managed_by)
        if self.can_access_in_all(permission_code) and not for_sync:
            client_groups = OperationalEntity.select(lambda oe: oe.id == -1) # This is a dummy to return count 0
        else:
            client_groups = self.get_client_group_with_permission(permission_code, for_sync=for_sync, managed_by=managed_by)
        if return_cg_ids:
            # There should always be few client groups for a user so we can list IDs
            # This boost performance A LOT when used in queries
            client_groups = select(cg.id for cg in client_groups)[:]
        if return_villages_ids:
            villages = select(v.id for v in villages)[:]
        return villages, client_groups

    def get_roles_with_permissions_for_mobile(self):
        return [{
            'id': r.id, 
            'name': r.name, 
            'permissions': [{
                'id': p.id, 
                'codeName': p.code_name
            } for p in r.permissions]
        } for r in self.get_roles()]

    def get_roles_in_entities_map(self):
        roles_entities_map = []
        for rie in self.roles_in_entities:
            role_in_entity = {}
            role_in_entity['entityId'] = rie.entity.id if rie.entity else None
            role_in_entity['roleId'] = rie.role.id if rie.role else None
            roles_entities_map.append(role_in_entity)
        return roles_entities_map

    def get_api_key(self, validity_time=3600):
        expiry_sec = validity_time
        expiry = SettingsService.get_setting('SessionLifetime')
        if expiry > 10:
            expiry_sec = expiry*60
        this_token = generate_jwt_for_user(self, expiry_sec)
        return this_token

    def get_authorization_level(self):
        return get_role_name_from_id(self.AuthorizationLevel.id)

    def get_role(self):
        return get_user_role(self.AuthorizationLevel.id)

    def get_roles(self):
        primary_role = self.get_role()
        all_roles = [primary_role]
        for rie in self.roles_in_entities:
            if rie.role:
                all_roles.append(rie.role)
        return all_roles

    @property
    def is_authenticated(self):
        expired = True
        with db_session:
            fresh_user = User.get(id=self.id)
            expired = fresh_user.is_expired() if fresh_user else True
        if expired:
            logout_user()
            return False
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self): # required by flask
        return self.id

    def get_link(self):
        return url_for('user.view_user', user_id=self.id)
    
    def get_display_id(self):
        return self.person.custom_id or str(self.id)

    def accounting_user(self):
        return accounting_db.AccountingUser.get(webUserID=self.id)

    def get_accounting_user(self):
        return accounting_db.AccountingUser.get(id=self.accountingUserID)

    def get_shops_list(self):
        return OperationalEntitiesGetterService.get_list(self)

    def get_interaction_topics(self, only_active=True):
        if only_active:
            topics = select(T for T in db.InteractionTopic if T.active == True)
        else:
            topics = select(T for T in db.InteractionTopic)
        return topics

    def get_last_three_interactions_from_client(self, thisClientId):
        from after_sales_system.interaction_system.services.interaction_service import \
            InteractionService
        return InteractionService.get_list(self, clients_ids=[thisClientId]).order_by(desc(db.InteractionReport.reportDate))[:3]

    def get_last_three_interactions_from_clients_mobile(self, clientIds):
        if not self.can_access_in_any('SyncInteractionsMobile'):
            return MockQuery([])
        iareports = []
        for clientId in clientIds:
            client_iareports = self.get_last_three_interactions_from_client(clientId)
            iareports = iareports + client_iareports
        return iareports

    def get_discussed_topics_for_mobile(self, cached_ids):
        if not config.ENABLE_ENTERPRISE_FEATURES:
            return MockQuery([])
        from core_system.client.services.client_getter_service import \
            ClientGetterService
        clients = ClientGetterService.get_list_for_mobile(self)
        client_ids = select(e.id for e in clients)[:]
        cached_ids['client'] = client_ids
        iareports = self.get_last_three_interactions_from_clients_mobile(client_ids)
        iareports_ids = [interaction_report.id for interaction_report in iareports]
        cached_ids['iareport'] = iareports_ids
        return select(
            topic for topic in db.DiscussedTopic
            if topic.interaction.id in iareports_ids
        )

    def get_relevant_survey_answers_for_mobile(self, cached_ids):
        from sales_system.leads.services.lead_getter_service import \
            LeadGetterService

        leads = LeadGetterService.get_list_for_mobile(self)
        leads_ids = select(l.id for l in leads)[:]
        cached_ids['lead'] = leads_ids
        
        # Enterprise-only: discussed topics
        if config.ENABLE_ENTERPRISE_FEATURES:
            discussed_topics = self.get_discussed_topics_for_mobile(cached_ids)
            discussed_topics_ids = select(e.id for e in discussed_topics)[:]
            cached_ids['discussed_topic'] = discussed_topics_ids
            interactions = select(sa.id for sa in db.SurveyAnswer if sa.discussed_topic.id in discussed_topics_ids and sa.is_last_answer)[:]
        else:
            cached_ids['discussed_topic'] = []
            interactions = []
        
        custom_forms = select(sa.id for sa in db.SurveyAnswer if sa.lead_answering.id in leads_ids and sa.is_last_answer)[:]
        return select(sa for sa in db.SurveyAnswer if sa.id in interactions+custom_forms)

    def get_cash_account(self):
        a = self.payment_wallets.select().first()
        if not a:
            full_name = self.full_name + ' (' + str(self.id) + ') [Cash]'
            a = db.PaymentWallet(
                RegistrationDate=datetime.now(),
                FullName=full_name,
                user=self,
                Type=PaymentWalletType.agent_collection,
                operator=''
            )
            PaymentWalletOwner(
                wallet=a,
                user=self,
                date=datetime.now(),
                balance=0
            )
        return a

    def get_relevant_contracts_for_mobile(self, clients_ids):
        from payg_loan_system.contracts.services.contract_list_service import \
            ContractListService
        contracts = ContractListService.get_from_clients_ids(clients_ids)
        return contracts

    def get_devices_for_mobile(self, contract_ids, lead_ids=None):
        from payg_loan_system.devices.device_list_service import \
            DeviceListService
        return DeviceListService.get_used_and_unused_devices(self, contract_ids, lead_ids)

    def get_sync_report(self, only_above=1000):
        import re
        report = []
        for entity,count in self.last_mobile_app_sync_report.items():
            if count > only_above:
                clean_name = " ".join(re.split("(?=[A-Z])", entity)).lower().capitalize()
                report.append(f'{clean_name}: {count}')
        return report

    def not_enabled_in_features_config(self, permission):
        needed_toggles = [
            toggle for toggle, perms in FEATURE_FLAGS_CONFIG.items() if permission in perms
        ]
        if not needed_toggles:
            return False
        # We check if any of the needed features are enabled
        toggles_enabled = SettingsService.get_setting('FeatureToggles')
        default = SettingsService.schema['FeatureToggles']['default']
        return not any(toggles_enabled.get(toggle, default[toggle]) for toggle in needed_toggles)
