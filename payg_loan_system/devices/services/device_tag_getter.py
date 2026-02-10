from payg_loan_system.devices.model.device import DeviceTag
from shared.services.base_getter_service import BaseGetterService
from shared.logger.loggers import Error
from shared.services.base_service import BaseService


class DeviceTagService(BaseGetterService, BaseService):

    OBJ_NAME = 'Device Tag'

    @classmethod
    def get_filtered_objects(cls, current_user, id=None, **kwargs):
        return DeviceTag.select().order_by(lambda t: t.name)

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        name = data.get('name')
        color = data.get('color', 'grey')
        cls._check_name(name)
        this_tag = DeviceTag(
            name=name,
            style=color
        )
        return this_tag
    
    @classmethod
    def _edit_from_data_and_user(cls, tag, data, user):
        name = data.get('name')
        color = data.get('color', tag.style)
        cls._check_name(name, tag)
        tag.name = name
        tag.style = color
        for device in tag.devices:
            device.tag_added()
        return tag

    @classmethod
    def _delete_from_object_and_user(cls, item, user):
        if item.devices.count() != 0:
            raise Error('Cannot remove tag associated with device')
        item.delete()

    @classmethod
    def extract_tags(cls, tags_string, user=None):
        try:
            tags_id = [int(tid) for tid in tags_string.split(',')]
            return DeviceTagService.get_list(user).filter(lambda t: t.id in tags_id)
        except ValueError:
            tags_name = tags_string.split(',')
            return DeviceTagService.get_list(user).filter(lambda t: t.name in tags_name)


    @classmethod
    def _check_name(cls, name, existing_device_tag=None):
        if not name:
            raise Error('Tags need to have a name')
        if ',' in name:
            raise Error('Name cannot contain the character ","')
        tag = DeviceTag.get(name=name)
        if tag:
            if not existing_device_tag or existing_device_tag != tag:
                raise Error('Tag name is already taken.')
