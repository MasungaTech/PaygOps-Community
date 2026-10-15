from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.services.edit_device_service import DeviceEditService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from payg_loan_system.devices.model.device import Device


class AllDeviceResource(BaseAPIResourceAll):
    LIST_SERVICE = DeviceGetterService
    LIST_PERMISSION = ['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock', 'OrphanedViewStock']
    MODEL = Device
    TAG = 'Devices'

    EXTRA_LIST_PARAMS = {
        'serial_number_without_prefix': {
            'in': 'query',
            "name": "serial_number_without_prefix",
            "description": "The serial number of the device without type prefix for an exact match (useful the type is not printed on the device)",
            "required": False,
            "example": '1234',
            "schema": {
                "type": "string"
            }
        }
    }


class IndividualDeviceResource(BaseAPIResourceIndividual):
    GET_SERVICE = DeviceGetterService
    GET_GLOBAL_PERMISSION = ['OrphanedViewStock']
    GET_PERMISSION = ['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock']
    OBJECT_NAME = 'Device'
    MODEL = Device
    TAG = 'Devices'
    EDIT_SERVICE = DeviceEditService
    EDIT_PERMISSION = ['EditTagsDevices', 'EditSubTypeDevices']
    ALLOWED_API_CALLER = ['post']
    SUBACTIONS = {
        'post': {
            'set_tags': {
                "name": "Set Device Tags",
                "permissions": ['EditTagsDevices'],
                "description": "Replace the device tags completely by a new set of tags",
                "properties": ["serial_number", "tags"]
            },
            'edit_tags': {
                "name": "Add/remove Device Tags",
                "permissions": ['EditTagsDevices'],
                "description": "Adds or removes specific tags to the device",
                "properties": ["serial_number", "add_tags", "remove_tags"]
            },
            'update_subtype': {
                "name": "Update Device sub-type",
                "permissions": ['EditSubTypeDevices'],
                "description": "Edit or removes the device sub-type",
                "properties": ["serial_number", "product_sub_type_id"]
            }
        }
    }

    ID_PARAM = {
        "name": "serial_number",
        "in": "path",
        "description": "The serial number of the device. It must contain the type prefix.",
        "property": "composed_serial",
        "required": True,
        "example": 'SOL-1234',
        "schema": {
            "type": "string"
        }
    }

    @classmethod
    def _get_relevant_entity(cls, this_object):
        item = this_object.stock_item
        if item.shop:
            return item.shop
        if item.user:
            return item.user.shop
    
    @classmethod
    def _get_relevant_person(cls, this_object):
        if this_object.stock_item.client:
            return this_object.stock_item.client.person
    