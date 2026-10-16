from messages_system.models.custom_message import CustomMessage
from shared.services.base_getter_service import BaseGetterService


class CustomMessageGetterService(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user=None, **kwargs):
        return CustomMessage.select()