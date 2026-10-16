from messages_system.models.custom_message import CustomMessage
from messages_system.services.custom_message_getter_service import CustomMessageGetterService
from messages_system.services.message_service import MessageService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual


class DeleteCustomMessageResource(BaseAPIResourceIndividual):
    MODEL = CustomMessage
    OBJECT_NAME = 'CustomMessage'
    TAG = 'Miscellaneous'
    GET_SERVICE = CustomMessageGetterService
    GET_PERMISSION = 'EditCustomSMSAdmin'
    DELETE_SERVICE = MessageService
    DELETE_PERMISSION = 'EditCustomSMSAdmin'

class AllCustomMessageResource(BaseAPIResourceAll):
    MODEL = CustomMessage
    OBJECT_NAME = 'CustomMessage'
    TAG = 'Miscellaneous'
    LIST_SERVICE = CustomMessageGetterService
    LIST_PERMISSION = 'EditCustomSMSAdmin'
    ADD_SERVICE = MessageService
    ADD_PERMISSION = 'EditCustomSMSAdmin'