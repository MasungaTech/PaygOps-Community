

from core_system.client.models import ClientTag
from shared.services.base_getter_service import BaseGetterService
from shared.logger.loggers import Error
from shared.services.base_service import BaseService


class ClientTagService(BaseGetterService):

    OBJ_NAME = 'Client Tag'

    @classmethod
    def get_filtered_objects(cls, current_user, id=None, **kwargs):
        return ClientTag.select().order_by(lambda t: t.name)

    @classmethod
    def get_from_user_and_id(cls, current_user, id=None, strict=False, **kwargs):
        return ClientTag.get(id=id)

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        name = data.get('name')
        color = data.get('color', 'grey')
        cls._check_name(name)
        this_tag = ClientTag(
            name=name,
            style=color
        )
        return this_tag
    
    @classmethod
    def _edit_from_data_and_user(cls, object, data, user):
        name = data.get('name')
        color = data.get('color', object.style)
        cls._check_name(name, object)
        object.name = name
        object.style = color
        return object

    @classmethod
    def _delete_from_object_and_user(cls, item, user):
        if item.clients.count() != 0:
            raise Error('Cannot remove tag associated with clients')
        item.delete()

    @classmethod
    def extract_tags(cls, tags_string, user=None):
        try:
            tags_id = [int(tid) for tid in tags_string.split(',')]
            return ClientTagService.get_list(user).filter(lambda t: t.id in tags_id)
        except ValueError:
            tags_name = tags_string.split(',')
            return ClientTagService.get_list(user).filter(lambda t: t.name in tags_name)

    @classmethod
    def _check_name(cls, name, existing_tag=None):
        if ',' in name:
            raise Error('Name can not contain the character ","')
        tag = ClientTag.get(name=name)
        if tag:
            if not existing_tag or existing_tag != tag:
                raise Error('Tag name is already taken.')