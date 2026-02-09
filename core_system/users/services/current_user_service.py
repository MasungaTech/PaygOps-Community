from core_system.operational_entities.models import OperationalEntity
from flask import request
from core_system.users.models.user_model import User
from pony.orm import db_session

class GatewayUser:
    id = 0
    full_name = 'Gateway'
    username = ''

    def reload(self):
        return self

    def can_access(self, permission, entity=None, person=None):
        return True

    def can_access_in_all(self, permission_code):
        return True

    def can_access_in_entities(self, permission_code, entities):
        return True
    
    def can_access_in_scope(self, permission, in_all=False):
        return True

    def can_access_in_any(self, permission):
        return True
    
    def get_entities_with_permission(self, permission, level=None):
        return OperationalEntity.select()
        

class UnauthorizedUser:
    id = -1
    full_name = 'Unauthorized User'
    username = ''

    def reload(self):
        return self

    def can_access(self, permission, entity=None, person=None):
        return False
    
    def can_access_in_all(self, permission):
        return False

    def can_access_in_entities(self, permission_code, entities):
        return False
    
    def can_access_in_scope(self, permission, in_all=False):
        return False

    def can_access_in_any(self, permission):
        return False

    def get_entities_with_permission(self, permission, level=None):
        return OperationalEntity.select(lambda oe: oe.id == -1)


@db_session
def get_current_api_user():
    key_payload = request.environ.get('token_payload')
    if not key_payload:
        return UnauthorizedUser()
    user_id = key_payload.get('sub')
    if user_id != 0:
        return User.get(id=user_id)
    return GatewayUser()
