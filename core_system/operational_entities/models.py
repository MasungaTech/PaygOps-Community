from shared.logger.loggers import Error
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from constants import FLOAT_OPTIONAL_OPTIONS, INTEGER_OPTIONAL_OPTIONS, REQUIRED_STRING_PATTERN
from datetime import datetime
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from pony.orm import Required, Optional, Set, Discriminator, select, composite_key

from core_system.core_entities import db

class UserWithRole(db.Entity, ModelDefinitionMixin):

    entity = Optional("OperationalEntity", column="entity")
    user = Required("User", column="user")
    role = Optional("Role", column="role")
    sync_entity = Required(bool, default=False)

    composite_key(entity, user)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "value": lambda o: o.id,
                    "description": "The unique ID of operational permission",
                    "example": 12,
                    "type": "integer"
                },
                'user_id': {
                    "value": lambda o: o.user.id,
                    "description": "The unique ID of the user associated with the operational permission",
                    "example": 123,
                    "type": "integer"
                },
                'entity_id': {
                    "value": lambda o: o.entity.id if o.entity else None,
                    "description": "The unique ID of the entity in which the user has the role (or null if applicable to all entities)",
                    "example": 123,
                    "oneOf": INTEGER_OPTIONAL_OPTIONS
                },
                'role_id': {
                    "value": lambda o: o.role.id if o.role else None,
                    "description": "The unique ID of the role that the user have in the affected entities (or null for the user's default role)",
                    "example": 123,
                    "oneOf": INTEGER_OPTIONAL_OPTIONS
                },
                'sync_enabled': {
                    "value": lambda o: o.sync_entity,
                    "description": "Whether the affected entity objects are synced to the mobile app (according the the permissions of the `role_id`)",
                    "example": True,
                    "default": False,
                    "type": "boolean"
                }
            },
            "create_required": ["user_id"],
            "create_allowed": [],
            "create_forbidden": ["id"],
            "edit_required": [],
            "edit_allowed": [],
            "edit_forbidden": ['id'],
            "view_required": [],
            "view_allowed": []
        }



class OperationalEntity(db.Entity, ModelDefinitionMixin):

    level = Discriminator(int)
    _discriminator_ = -2

    ascendants = Set("OperationalEntity", column="higher", table="operational_entities_ascendants", reverse="descendants")
    descendants = Set("OperationalEntity", column="lower")

    name = Required(str)
    code = Optional(str)
    user_in_charge = Optional("User", reverse="managed_operational_entities", column="user_in_charge")
    users_with_roles = Set("UserWithRole")

    description = Optional(str)

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = Optional(str, unique=True)

    addon_offers_allowed_for_leads = Set("AddOnOffer", reverse="entities_allowed_for_leads", column="addonofferwrapper")
    addon_offers_allowed_for_contracts = Set("AddOnOffer", reverse="entities_allowed_for_contracts", column="addonofferwrapper")

    offers_allowed_for_leads = Set("Offer", reverse="entities_allowed_for_leads")
    offers_allowed_for_contracts = Set("Offer", reverse="entities_allowed_for_contracts")

    # To be removed after migration
    old_addon_offers_allowed_for_leads = Set("AddOnOfferVersion", reverse="r_entities_allowed_for_leads", column="addonoffer")
    old_addon_offers_allowed_for_contracts = Set("AddOnOfferVersion", reverse="r_entities_allowed_for_contracts", column="addonoffer")

    def before_insert(self):
        self.check_data_coherence()
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    def before_update(self):
        self.modifiedDate = datetime.now()

    @property
    def is_client_group(self):
        return self._discriminator_ == -1

    def get_link(self):
        from flask import url_for
        return url_for('entities.view_entity', entity_id=self.id)

    def get_display_id(self):
        return str(self.id)


class ClientGroup(OperationalEntity):

    _discriminator_ = -1
    persons = Set("Person")

    def after_update(self):
        self.check_data_coherence()

    def after_insert(self):
        self.ascendants.add(self)
        self.check_data_coherence()

    def check_data_coherence(self):
        if ClientGroup.select(lambda g: g.name == self.name and g != self).exists():
            raise Error(f"Client group with name {self.name} already exists")

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "value": lambda o: o.id,
                    "description": "The unique id of the client group",
                    "example": 12,
                    "type": "integer"
                },
                'name': {
                    "value": lambda o: o.name,
                    "description": "The name of the client group",
                    "example": "My Group",
                    "type": "string",
                    "minLength": 1,
                    "pattern": REQUIRED_STRING_PATTERN
                    },
                'user_in_charge_id': {
                    "value": lambda o: o.user_in_charge.id,
                    "description": "The id of the user in charge",
                    "example": 123,
                    "oneOf": INTEGER_OPTIONAL_OPTIONS
                },
                'description': {
                    "value": lambda o: o.description,
                    "description": "The description/notes of the operational entity",
                    "example": "Any additional information about the entity",
                    "type": "string"
                },
            },
            "create_required": ["name", "user_in_charge_id"],
            "create_allowed": [],
            "create_forbidden": ["id"],
            "edit_required": [],
            "edit_allowed": [],
            "edit_forbidden": ['id'],
            "view_required": [],
            "view_allowed": []
        }

class HierarchicalOperationalEntity(OperationalEntity):

    parent = Optional("HierarchicalOperationalEntity", column="parent", reverse="children")
    children = Set("HierarchicalOperationalEntity")

    _discriminator_ = -2
    latitude = Optional(float)
    longitude = Optional(float)

    admin_contact_name = Optional(str)
    admin_phone_number = Optional(str)
    population = Optional(int)

    notifications = Set("Notification")
    destined_stock = Set("StockMovement")
    quantity_stock_locations = Set('QuantityStockLocation')

    reference_of_users = Set("User")

    offers = Set("Offer")

    composite_key("level", "name", parent)

    def rebuild_ascendants(self):
        self.ascendants.clear()
        self.ascendants.add(self)
        if self.parent:
            self.ascendants.add(self.parent)
            self.ascendants.add(self.parent.ascendants)
        for child in self.children:
            child.rebuild_ascendants()
            child.modifiedDate = datetime.now()

    def check_data_coherence(self):
        from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
        if self.parent and self.parent.level != self.level+1:
            raise Error(f'Incorrect parent asignation, entity of level {self.level} and parent of level {self.parent.level}')
        if self.level < 4:
            if not self.parent:
                raise Error(f'Entities of level {self.level} must have a parent')
        if not self.inherited_user_in_charge:
            raise Error(f'A user in charge could not be found for this entity, please add one to it or to its ancestors')
        self.rebuild_ascendants()
    
    def after_insert(self):
        self.check_data_coherence()

    def after_update(self):
        self.check_data_coherence()

    @property
    def not_empty_code(self):
        return int(self.code or self.id)

    @property
    def inherited_user_in_charge(self):
        return self.user_in_charge if self.user_in_charge else self.parent.inherited_user_in_charge if self.parent else None

    def get_leads(self):
        return select(l for l in db.Lead if (l.person.village in self.descendants))
    
    def get_active_leads(self):
        return self.get_leads().filter(lambda l: l.active)

    def get_clients(self, active=True):
        clients = select(c for c in db.Client if (c.person.village in self.descendants))
        return clients.filter(lambda c: c.active) if active else clients
    
    def get_ancestor_of_level(self, level):
        if level < self.level:
            return None
        ancestor = self
        while ancestor.level != level:
            ancestor = ancestor.parent
        return ancestor

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "value": lambda o: o.id,
                    "description": "The unique id of the operational entity",
                    "example": 12,
                    "type": "integer"
                },
                'level': {
                    "value": lambda o: o.level,
                    "description": "The level of the operational entity",
                    "example": 1,
                    "type": "integer"
                },
                'name': {
                    "value": lambda o: o.name,
                    "description": "The name of the operational entity",
                    "example": "My village",
                    "type": "string"
                },
                'old_id': {
                    "value": lambda o: o.code,
                    "deprecated": True,
                    "description": "The old ID of the operational entity",
                    "example": "REF1234",
                    "type": "string"
                },
                'parent_id': {
                    "value": lambda o: o.parent.id if o.parent else None,
                    "description": "The id of the parent entity",
                    "example": 123,
                    "oneOf": INTEGER_OPTIONAL_OPTIONS
                },
                'gps_longitude': {
                    "value": lambda o: o.longitude,
                    "description": "The longitude coordinate of the GPS location of the operational entity",
                    "example": 75.54657,
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "minimum": -180,
                    "maximum": 180,
                },
                'gps_latitude': {
                    "value": lambda o: o.latitude,
                    "description": "The latitude coordinate of the GPS location of the operational entity",
                    "example": 15.54657,
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "minimum": -90,
                    "maximum": 90,
                },
                'admin_contact_name': {
                    "value": lambda o: o.admin_contact_name,
                    "description": "The name of the operational entity administrative contact",
                    "example": "Name Surname",
                    "type": "string"
                },
                'admin_phone_number': {
                    "value": lambda o: o.admin_phone_number,
                    "description": "The phone number of the operational entity administrative contact",
                    "example": "+45234442354",
                    "type": "string"
                },
                'population': {
                    "value": lambda o: o.population,
                    "description": "The population of the operational entity",
                    "example": 12000,
                    "oneOf": INTEGER_OPTIONAL_OPTIONS
                },
                'description': {
                    "value": lambda o: o.description,
                    "description": "The description/notes of the operational entity",
                    "example": "Any additional information about the entity",
                    "type": "string"
                },
                'user_in_charge_id': {
                    "value": lambda o: o.user_in_charge.id if o.user_in_charge else None,
                    "description": "The id of the user in charge",
                    "example": 123,
                    "oneOf": INTEGER_OPTIONAL_OPTIONS
                },
                'l0_entity_id': {
                    "value": lambda o: o.l0_entity.id if o.l0_entity else None,
                    "description": "The unique id of the related L0 operational entity",
                    "example": 17,
                    "type": "integer"
                },
                'l1_entity_id': {
                    "value": lambda o: o.l1_entity.id if o.l1_entity else None,
                    "description": "The unique id of the related L1 operational entity",
                    "example": 12,
                    "type": "integer"
                },
                'l2_entity_id': {
                    "value": lambda o: o.l2_entity.id if o.l2_entity else None,
                    "description": "The unique id of the related L2 operational entity",
                    "example": 19,
                    "type": "integer"
                },
                'l3_entity_id': {
                    "value": lambda o: o.l3_entity.id if o.l3_entity else None,
                    "description": "The unique id of the related L3 operational entity",
                    "example": 22,
                    "type": "integer"
                },
                'l4_entity_id': {
                    "value": lambda o: o.l4_entity.id,
                    "description": "The unique id of the related L4 operational entity",
                    "example": 31,
                    "type": "integer"
                },
            },
            "create_required": ["name"],
            "create_allowed": [],
            "create_forbidden": ["id", "l0_entity_id", "l1_entity_id", "l2_entity_id", "l3_entity_id", "l4_entity_id", "old_id"],
            "edit_required": [],
            "edit_allowed": [],
            "edit_forbidden": ['id', 'level', "l0_entity_id", "l1_entity_id", "l2_entity_id", "l3_entity_id", "l4_entity_id", "old_id"],
            "view_required": [],
            "view_allowed": None
        }


class Village(HierarchicalOperationalEntity):
    _discriminator_ = 0

    old_persons = Set('PersonEntityChange', cascade_delete=True, reverse="old_entity")
    new_persons = Set('PersonEntityChange', cascade_delete=True, reverse="new_entity")
    persons = Set("Person")

    def before_delete(self):
        if db.Person.select(lambda p: p.village.id == self.id):
            raise Error('Cannot delete villages with persons assigned to it')

    @property
    def l0_entity(self):
        return self

    @property
    def l1_entity(self):
        return self.parent
    
    @property
    def l2_entity(self):
        return self.parent.parent

    @property
    def l3_entity(self):
        return self.parent.parent.parent

    @property
    def l4_entity(self):
        return self.parent.parent.parent.parent

    @property
    def all_ancestors(self):
        return [self.l1_entity, self.l2_entity, self.l3_entity, self.l4_entity]

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "value": lambda o: o.not_empty_code,
                    "description": "The old id of the village",
                    "example": 12,
                    "type": "integer"
                },
                'name': {
                    "value": lambda o: o.name,
                    "description": "The name of the village",
                    "example": "My village",
                    "type": "string"
                },
                'cluster_id': {
                    "value": lambda o: int(o.parent.not_empty_code),
                    "description": "The id of the parent entity",
                    "example": 123,
                    "type": "integer"
                },
                'gps_longitude': {
                    "value": lambda o: o.longitude,
                    "description": "The longitude coordinate of the GPS location of the village",
                    "example": 75.54657,
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "minimum": -180,
                    "maximum": 180,
                    "example": 60.325389,
                },
                'gps_latitude': {
                    "value": lambda o: o.latitude,
                    "description": "The latitude coordinate of the GPS location of the village",
                    "example": 15.54657,
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "minimum": -90,
                    "maximum": 90,
                },
                'entity_id': {
                    "value": lambda o: o.id,
                    "type": "integer",
                    "description": "The new unique ID of the Village",
                    "example": 123
                },
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }

    @property
    def shop_name(self):
        if self.parent is not None:
            return self.parent.parent.name
        return ' - '

    def GetActiveLeadCount(self):
        return self.get_active_leads().count()


class Cluster(HierarchicalOperationalEntity):

    _discriminator_ = 1

    @property
    def l0_entity(self):
        return None

    @property
    def l1_entity(self):
        return self
    
    @property
    def l2_entity(self):
        return self.parent

    @property
    def l3_entity(self):
        return self.parent.parent

    @property
    def l4_entity(self):
        return self.parent.parent.parent

    @property
    def all_ancestors(self):
        return [self.l2_entity, self.l3_entity, self.l4_entity]

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "value": lambda o: o.code,
                    "description": "The old unique ID of the cluster",
                    "type": "integer",
                    "example": 12
                },
                'name': {
                    "value": lambda o: o.name,
                    "description": "The name of the cluster",
                    "type": "string",
                    "exmaple": "Cluster Name"
                },
                'hub_id': {
                    "value": lambda o: int(o.parent.not_empty_code),
                    "description": "The unique ID of the cluster's hub",
                    "type": "integer",
                    "example": 12
                },
                'manager_user_id': {
                    "value": lambda o: o.user_in_charge.id if o.user_in_charge else None,
                    "description": "The unique ID of the user managing the cluster",
                    "type": "integer",
                    "example": 12
                },
                'entity_id': {
                    "value": lambda o: o.id,
                    "type": "integer",
                    "description": "The new unique ID of the Cluster",
                    "example": 123
                },
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }

class Hub(HierarchicalOperationalEntity):
    _discriminator_ = 2

    @property
    def l0_entity(self):
        return None

    @property
    def l1_entity(self):
        return None
    
    @property
    def l2_entity(self):
        return self

    @property
    def l3_entity(self):
        return self.parent

    @property
    def l4_entity(self):
        return self.parent.parent

    @property
    def all_ancestors(self):
        return [self.l3_entity, self.l4_entity]

    def get_clients(self, active=True):
        clients = select(c for c in db.Client if (c.person.village.parent.parent == self))
        return clients.filter(lambda c: c.active) if active else clients

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "value": lambda o: o.code,
                    "type": "integer",
                    "description": "The (old) unique ID of the Hub",
                    "example": 123
                },
                'name': {
                    "value": lambda o: o.name,
                    "type": "string",
                    "description": "The name of the Hub",
                    "example": "Hub name"
                },
                'entity_id': {
                    "value": lambda o: o.id,
                    "type": "integer",
                    "description": "The new unique ID of the Hub",
                    "example": 123
                },
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }

    def get_users(self):
        return select(uwr.user for uwr in self.users_with_roles)

class Zone(HierarchicalOperationalEntity):
    _discriminator_ = 3

    @property
    def l0_entity(self):
        return None

    @property
    def l1_entity(self):
        return None
    
    @property
    def l2_entity(self):
        return None

    @property
    def l3_entity(self):
        return self

    @property
    def l4_entity(self):
        return self.parent

    @property
    def all_ancestors(self):
        return [self.l4_entity]

class Region(HierarchicalOperationalEntity):
    _discriminator_ = 4

    @property
    def l0_entity(self):
        return None

    @property
    def l1_entity(self):
        return None
    
    @property
    def l2_entity(self):
        return None

    @property
    def l3_entity(self):
        return None

    @property
    def l4_entity(self):
        return self

    @property
    def all_ancestors(self):
        return []
