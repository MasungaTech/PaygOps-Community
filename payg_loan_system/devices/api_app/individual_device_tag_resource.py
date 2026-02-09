from payg_loan_system.devices.model.device import DeviceTag
from payg_loan_system.devices.services.device_tag_getter import DeviceTagService
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual


class IndividualDeviceTagResource(BaseAPIResourceIndividual):

    GET_SERVICE = DeviceTagService
    EDIT_SERVICE = DeviceTagService  
    DELETE_SERVICE = DeviceTagService
    EDIT_PERMISSION = 'CreateTagsDevices'
    DELETE_PERMISSION = 'CreateTagsDevices'
    OBJECT_NAME = 'Device Tag'
    MODEL = DeviceTag
    TAG = 'Tags'
