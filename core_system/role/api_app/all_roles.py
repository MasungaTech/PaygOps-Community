from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from core_system.role.models import Role
from core_system.role.services import RoleGetterService, PermissionService


class AllRolesResource(BaseAPIResourceAll):

    LIST_SERVICE = RoleGetterService
    ADD_SERVICE = PermissionService
    LIST_PERMISSION = 'ViewRoles'
    GLOBAL_LIST_PERMISSION = 'AssignRoles'
    ADD_PERMISSION = 'CreateRoles'
    GLOBAL_ADD_PERMISSION = 'CreateRoles'
    MODEL = Role
    TAG = 'Roles'
    EXTRA_LIST_PARAMS = {
        'search': {
            'in': 'query',
            'name': 'search',
            'schema': {
                'type': 'string',
            },
            'example': 'Agent',
            'allowEmptyValue': True,
            'description': 'Allows for filtering roles by name'
        },
    }
