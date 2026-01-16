from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from core_system.client.models import ClientTag
from core_system.client.services.client_tag_getter import ClientTagService


class IndividualTagResource(BaseAPIResourceIndividual):

    GET_SERVICE = ClientTagService
    EDIT_SERVICE = ClientTagService
    DELETE_SERVICE = ClientTagService
    EDIT_PERMISSION = 'CreateTagsClients'
    DELETE_PERMISSION = 'CreateTagsClients'
    OBJECT_NAME = 'Tag'
    MODEL = ClientTag
    TAG = 'Tags'
