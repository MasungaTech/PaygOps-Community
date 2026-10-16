from core_system.role import Required, Set, Optional
from core_system.core_entities import db
from enum import Enum, unique
from datetime import datetime
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
import config



class Role(db.Entity, ModelDefinitionMixin):
    name = Required(str, unique=True)
    permissions = Set("Permission")
    users = Set("User", cascade_delete=False)
    users_in_entities = Set("UserWithRole", cascade_delete=False)
    # User journey editor is enterprise-only. In OSS mode we keep the reverse FK
    # column as integers so Pony doesn't require the UserJourneyVersion entity.
    if getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False):
        user_journey_version = Set("UserJourneyVersion", cascade_delete=False, reverse="allowed_roles")
    type = Required(int)

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    def get_role_type_name(self):
        return get_role_type_name(self.type)
    
    def get_link(self):
        from flask import url_for
        return url_for('permissions.edit_role', role_id=self.id)

    def get_display_id(self):
        return str(self.id)
    
    def before_insert(self):
        self.modifiedDate = datetime.now()

    def before_update(self):
        self.modifiedDate = datetime.now()
    
    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "This is the ID of the Role."
                },
                'name': {
                    "description": "This is the name of the Role.",
                    "type": "string",
                    "example": "Shop Manager",
                    "value": lambda o: o.name
                },
                'type': {
                    "description": "This is the type of the Role.",
                    "type": "string",
                    "enum": [rt for rt in ROLE_TYPE_IDS],
                    "example": 0,
                    "value": lambda o: ROLE_TYPE_NAMES[o.type]
                },
                'permissions': {
                    "description": "This is the list of permissions included in the role",
                    "example": ["AddLeads", "ViewClients"],
                    "value": lambda o: [p.code_name for p in o.permissions]
                },
            },
            "create_required": ['name', 'type', 'permissions'],
            "create_allowed": ['name', 'type', 'permissions'],
            "edit_required": [],
            "edit_allowed": ['name', 'type', 'permissions'],
            "view_required": [],
            "view_allowed": None
        }


class Permission(db.Entity):
    REQUIRED_CODE_NAMES = ['ViewClients', 'ViewLeads']

    name = Required(str, unique=True)  # used for what the user sees in the create role
    code_name = Required(str, unique=True)  # used in code for view permissions
    max_value = Optional(int)
    min_value = Optional(int)
    roles = Set("Role")

    @classmethod
    def has_one_required_permission(cls, permissions):
        return any(p.code_name in cls.REQUIRED_CODE_NAMES for p in permissions)


@unique
class RoleType(Enum):
    OTHER = 0
    AGENT = 1
    MANAGER = 2
    ADMIN = 3
    API = 4


def get_role_type_name(role_id):
    return ROLE_TYPE_NAMES[role_id]


ROLE_TYPE_NAMES = {0: 'Other', 1: 'Agent', 2: 'Manager', 3: 'Admin', 4: 'API'}
ROLE_TYPE_IDS = {'Other': 0, 'Agent': 1, 'Manager': 2, 'Admin': 3, 'API': 4}
