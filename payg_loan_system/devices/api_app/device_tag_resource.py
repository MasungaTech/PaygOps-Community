from payg_loan_system.devices.model.device import DeviceTag
from payg_loan_system.devices.services.device_tag_getter import DeviceTagService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll


class DeviceTagsResource(BaseAPIResourceAll):

    LIST_SERVICE = DeviceTagService
    ADD_SERVICE = DeviceTagService
    ADD_PERMISSION = 'CreateTagsDevices'
    MODEL = DeviceTag
    TAG = 'Tags'