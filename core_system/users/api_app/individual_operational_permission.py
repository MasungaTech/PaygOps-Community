from core_system.operational_entities.models import UserWithRole
from core_system.users.services.operational_permissions_service import OperationalPermissionsService
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual



class IndividualOperationalPermissionsResource(BaseAPIResourceIndividual):

    GET_SERVICE = OperationalPermissionsService
    GET_PERMISSION = 'ViewUsers'
    GET_GLOBAL_PERMISSION = 'ViewUsers'
    EDIT_SERVICE = OperationalPermissionsService
    EDIT_PERMISSION = 'EditUsers'
    EDIT_GLOBAL_PERMISSION = 'EditUsers'
    DELETE_SERVICE = OperationalPermissionsService
    DELETE_PERMISSION = 'EditUsers'
    DELETE_GLOBAL_PERMISSION = 'EditUsers'
    OBJECT_NAME = 'Operational Permission'
    MODEL = UserWithRole
    TAG = 'Users'

    @classmethod
    def _get_relevant_entity(cls, this_object):
        return this_object.entity
