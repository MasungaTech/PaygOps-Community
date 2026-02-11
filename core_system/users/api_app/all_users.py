from core_system.users.services.user_getter_service import UserGetterService
from core_system.users.models.user_model import User
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from core_system.users.services.edit_user_service import EditUserService


class AllUsersResource(BaseAPIResourceAll):

    LIST_SERVICE = UserGetterService
    ADD_SERVICE = EditUserService
    LIST_PERMISSION = 'ViewUsers'
    ADD_PERMISSION = 'AddUsers'
    MODEL = User
    TAG = 'Users'
    EXTRA_LIST_PARAMS = {
        'active': {
            'in': 'query',
            'name': 'active',
            'schema': {
                'type': 'string',
                "enum": ['active', 'inactive', 'all'],
                "default": "all"
            },
            "example": "all",
            'allowEmptyValue': True,
            'description': 'Allows for filtering just active users'
        },
    }
