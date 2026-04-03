from payg_loan_system.devices.model.device_notes_model import DeviceNote
from payg_loan_system.devices.services.device_note_service import DeviceNoteService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual


class DeviceNotesIndividualResource(BaseAPIResourceIndividual):
    GET_SERVICE = DeviceNoteService
    EDIT_SERVICE = DeviceNoteService
    DELETE_SERVICE = DeviceNoteService
    GET_PERMISSION = ['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock']
    GET_GLOBAL_PERMISSION = 'OrphanedViewStock'
    EDIT_GLOBAL_PERMISSION = 'DeleteNotesDevices'
    DELETE_GLOBAL_PERMISSION = 'DeleteNotesDevices'
    MODEL = DeviceNote
    OBJECT_NAME = 'Device Note'
    TAG = 'Devices'


class DeviceNotesAllResource(BaseAPIResourceAll):
    LIST_SERVICE = DeviceNoteService
    ADD_SERVICE = DeviceNoteService
    LIST_PERMISSION = ['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock', 'OrphanedViewStock']
    ADD_PERMISSION = 'AddNotesDevices'
    MODEL = DeviceNote
    TAG = 'Devices'

    EXTRA_LIST_PARAMS = {
        'device_serial_number': {
            'in': 'path',
            "name": "device_serial_number",
            "description": "The serial_number of the device",
            "required": True,
            "example": 'SOL-1234',
            "schema": {
                "type": "string"
            }
        },
    }
    EXTRA_POST_PARAMS = EXTRA_LIST_PARAMS
