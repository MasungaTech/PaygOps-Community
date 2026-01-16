from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from core_system.role.models import Role
from core_system.role.services import RoleGetterService, PermissionService



class IndividualRoleResource(BaseAPIResourceIndividual):

    GET_SERVICE = RoleGetterService
    EDIT_SERVICE = PermissionService
    DELETE_SERVICE = PermissionService
    GET_PERMISSION = 'AssignRoles'
    GET_GLOBAL_PERMISSION = 'AssignRoles'
    EDIT_PERMISSION = 'CreateRoles'
    EDIT_GLOABL_PERMISSION = 'CreateRoles'
    DELETE_PERMISSION = 'CreateRoles'
    DELETE_GLOABL_PERMISSION = 'CreateRoles'
    OBJECT_NAME = 'Role'
    MODEL = Role
    TAG = 'Roles'
