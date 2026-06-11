from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.model.device_notes_model import DeviceNote
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService
from shared.services.base_service import BaseService
from datetime import datetime



class DeviceNoteService(BaseGetterService, BaseService):

    OBJ_NAME = 'Device Note'

    @classmethod
    def _delete_from_object_and_user(cls, note, user):
        note.delete()

    @classmethod
    def preprocess_list_filters(cls, user, **kwargs):
        params = {}
        if 'device_serial_number' in kwargs:
            params['device'] = DeviceGetterService.get_from_user_and_properties(user, strict=True, composed_serial=kwargs['device_serial_number'])
        return params

    @classmethod
    def get_filtered_objects(cls, current_user, id=None, device=None, **kwargs):
        if device:
            return device.notes
        return DeviceNote.select()

    @classmethod
    def _add_from_data_and_user(cls, data, user, device_serial_number):

        this_device = DeviceGetterService.get_from_user_and_properties(user, strict=True, composed_serial=device_serial_number)
        if this_device.notes.count() >= 50:
            raise Error('This device has already reached the limit of 50 notes')
        note = DeviceNote(
            content=data['content'],
            user=user,
            time=datetime.now(),
            device=this_device
        )
        this_device.tag_added()
        return note

    @classmethod
    def _edit_from_data_and_user(cls, note, data, user):
        note.content = data['content']
        note.device.tag_added()
        return note
