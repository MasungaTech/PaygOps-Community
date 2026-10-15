from core_system.client.models import ClientTag
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from core_system.client.services.client_tag_getter import ClientTagService


class AllTagsResource(BaseAPIResourceAll):

    LIST_SERVICE = ClientTagService
    ADD_SERVICE = ClientTagService
    ADD_PERMISSION = 'CreateTagsClients'
    MODEL = ClientTag
    TAG = 'Tags'
