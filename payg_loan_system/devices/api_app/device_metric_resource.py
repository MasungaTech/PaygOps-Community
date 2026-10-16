from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.model.settings_model import Settings
from payg_loan_system.devices.services.device_metrics_service import DeviceMetricsService, Metric


class DeviceMetricsResourceAll(BaseAPIResourceAll):

    LIST_SERVICE = DeviceMetricsService
    LIST_PERMISSION = LIST_PERMISSION = ['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock', 'OrphanedViewStock']
    MODEL = Metric
    TAG = 'Devices'

    EXTRA_LIST_PARAMS = {
        'device_serial_number': {
            'in': 'query',
            "name": "device_serial_number",
            "description": "The serial_number of the device",
            "example": 'SOL-1234',
            "schema": {
                "type": "string"
            }
        },
        'name': {
            'in': 'query',
            "name": "name",
            "description": "The name of the metric",
            "example": 'Instant Power',
            "schema": {
                "type": "string"
            }
        }
    }
