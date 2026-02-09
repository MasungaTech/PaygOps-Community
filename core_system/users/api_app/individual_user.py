from core_system.users.services.edit_user_service import EditUserService
from core_system.users.models.user_model import User
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from core_system.users.services.user_getter_service import UserGetterService


class IndividualUserResource(BaseAPIResourceIndividual):

    GET_SERVICE = UserGetterService
    EDIT_SERVICE = EditUserService
    GET_PERMISSION = 'ViewUsers'
    EDIT_PERMISSION = 'EditUsers'
    OBJECT_NAME = 'User'
    MODEL = User
    TAG = 'Users'

    @classmethod
    def _get_relevant_entity(cls, this_object):
        return this_object.shop

