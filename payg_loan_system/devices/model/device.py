from datetime import datetime
from decimal import Decimal
from constants import INTEGER_OPTIONAL_OPTIONS, OPTIONAL_STRING_OPTIONS
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from pony.orm import Required, Optional, Set, Json, exists, select, desc
from core_system.core_entities import db
from payg_loan_system.devices.model.device_interfaces import BaseDeviceClass
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.model.device_notes_model import DeviceNote
from payg_loan_system.devices.model.offline_token_model import OfflineToken
from payg_loan_system.devices.model.device_mode import DeviceMode
from payg_loan_system.requests.models import ActivationRequest
from payg_loan_system.devices.model.device_metrics_model import MetricFormat
from shared.model.interface import ModelInterface
from shared.services.settings_service import SettingsService
from shared.cache.redis_config import delete_cache_key
from config import DEVICE_CACHE_KEY_PREFIX, DEVICE_MODE_NAMES
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.services.settings_service import SettingsService
from shared.cache.redis_config import get_cache_key, set_cache_key
from shared.model.cached_model import CachedModelMixin
import config


class Device(db.Entity, BaseDeviceClass, ModelDefinitionMixin, CachedModelMixin):
    composed_serial = Required(str, unique=True, index=True)
    type = Required(str)
    Mode = Required(int, py_check=DeviceMode.valid)
    stock_item = Required('StockItem', column="stock_item")

    SerialNumber = Optional(str, index=True)
    RegistrationTime = Optional(datetime)
    ActiveUntil = Optional(datetime)

    contract = Optional('Contract')

    credit_balance = Optional(Decimal)
    allowed_units = Optional(Json)
    credit_unit = Optional(str)
    mobile_uuid = Optional(str, unique=True)
    supports_monitoring_data = Optional(bool)
    new_data_hook_uuid = Optional(str)

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    allocated_lead = Optional('Lead')

    product_sub_type = Optional(ProductSubType)
    addon = Optional('ContractAddOn')

    # Cached data
    cached_data = Optional(Json, volatile=True)

    # FKs
    tokens = Set('Token')
    metrics = Set('Metric')
    offline_tokens = Set(OfflineToken)
    notes = Set(DeviceNote)
    contract_event_old_device = Set('ContractEvent')
    contract_event_new_device = Set('ContractEvent')
    ActivationRequests = Set(ActivationRequest)
    MentorRequests = Set("MentorRequest")
    tags = Set("DeviceTag")
    transaction_requests = Set('TransactionRequest')
    if config.ENABLE_ENTERPRISE_FEATURES:
        tasks = Set('Task')


    def update_cached_data(self, type_map=None):
        if not self.cached_data:
            self.cached_data = {}
        if getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False):
            from mobile_sync_system.factories.device_factory import DeviceFactory
            self.cached_data['mobile_object'] = DeviceFactory.map_server_to_mobile_core(self, type_map)
        else:
            self.cached_data['mobile_object'] = {}

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
    
    def after_insert(self):
        self.update_cached_data()

    def get_client(self):
        return getattr(self.contract, 'client', None)

    def tag_added(self):
        self.modifiedDate = datetime.now()
        
    def get_display_name(self):
        if self.type == SettingsService.get_setting('FallBackDeviceType') \
                and SettingsService.get_setting('HidePrefixFallBackDeviceType'):
            return str(self.SerialNumber)
        return self.composed_serial

    def get_link(self):
        from flask import url_for
        return url_for('device.view_device', device_id=self.id)

    def get_display_id(self):
        return self.get_display_name()
    
    def get_first_activation(self):
        activation = self.ActivationRequests.order_by(lambda d: d.ReceptionTime).first()
        return activation.ReceptionTime if activation else None

    def get_type_name(self):
        return DeviceAPIService.get_device_human_readable_type_name(self.type)

    def get_mode_name(self):
        return DEVICE_MODE_NAMES.get(self.Mode, 'Unknown')

    def get_active_until_if_payg(self):
        return self.ActiveUntil if self.Mode == DeviceMode.time else None

    def get_api_data(self):
        api_data = SettingsService.get_setting('AllDeviceAPIS')
        return api_data.get(self.type, {})

    def api_type(self, cached=False):
        if cached:
            cached_type = get_cache_key(self.type)
            if cached_type:
                return cached_type
        
        api_type = self.get_api_data().get('device_api_type')
        device_type = api_type or 'NOT_DEFINED'

        if cached:
            set_cache_key(self.type, device_type)

        return device_type

    def get_last_usage_metrics(self, metric_type):
        return self.metrics.filter(lambda m: m.metric_type.uuid == metric_type).order_by(lambda m: desc(m.time)).first()

    def get_usage_metrics_by_date(self, start_date, end_date, metric_type):
        return self.metrics.filter(lambda m: m.time.date() >= start_date \
                                    and m.time.date() <= end_date \
                                    and m.metric_type == metric_type)

    def has_gps_metrics(self):
        return exists(metric for metric in self.metrics if metric.metric_type.format == MetricFormat.gps)

    def last_gps_coordinates(self):
        last_gps = None
        if self.has_gps_metrics():
            last_gps_obj = select(m for m in self.metrics if m.metric_type.format == MetricFormat.gps).order_by(lambda m: desc(m.time)).first()
            if last_gps_obj:
                last_gps = last_gps_obj.value, last_gps_obj.secondary_value
        return last_gps

    def used_metric_units(self, include_gps=True, include_string=True, objects=False):
        base = self.metrics
        if not include_gps:
            base = base.filter(lambda m: not m.metric_type.format == MetricFormat.gps)
        if not include_string:
            base = base.filter(lambda m: not m.metric_type.format == MetricFormat.string)

        types = select(m.metric_type for m in base)
        types = sorted(types, key=lambda obj: obj.id)
        if objects:
            return [m.get_serialized_object() for m in types]
        return [m.uuid for m in types]
    
    def before_update(self):
        self.modifiedDate = datetime.now()
        self.update_cached_data()

    def after_update(self):
        cache_key = DEVICE_CACHE_KEY_PREFIX + str(self.id)
        delete_cache_key(cache_key)


    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 99,
                    "description": "The internal ID of the device. ",
                    "value": lambda o: o.id
                },
                'serial_number': {
                    "type": "string",
                    "example": 'SOL-1234',
                    "description": "The serial number of the device. ",
                    "value": lambda o: o.composed_serial
                },
                'contract': {
                    "type": "string",
                    "example": 'C12345001',
                    "description": "The reference of the contract to which the device is linked. ",
                    "value": lambda o: getattr(o.contract, 'reference', None)
                },
                'expiration_time': {
                    "type": "string",
                    "format": "date-time",
                    "example": datetime(2020, 6, 15).isoformat(),
                    "description": "The time at which the device\'s credit will expire. ",
                    "value": lambda o: o.ActiveUntil.isoformat() if o.ActiveUntil else None
                },
                "tags": {
                    "oneOf": [{
                        "type": "string",
                    }, {
                        "type": "array",
                    }],
                    "example": ["tag1", "tag2", "tag3"],
                    "value": lambda o: [t.name for t in o.tags],
                    "description": "The tags associated with the device. Use `add_tags` and `remove_tags` to modify the tags rather than editing `tags` directly."
                },
                "new_tags": {
                    "type": "string",
                    "items": {
                        "type": "string"
                    },
                    "example": "tag1, tag2, tag3",
                    "deprecated": True,
                },
                "removed_tags": {
                    "type": "string",
                    "items": {
                        "type": "string"
                    },
                    "deprecated": True,
                },
                "add_tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "example": ["tag1", "tag2", "tag3"],
                    "description": "Pass tags here to be added to the device. To choose the colour create the tag on the UI before adding it here. ",
                },
                "remove_tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "example": ["tag2", "tag3"],
                    "description": "Pass tags here to be removed to the device.",
                },
                "product_sub_type_id": {
                    "description": "The product sub-type ID, if applicable",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 1,
                    "value": lambda o: o.product_sub_type.id if o.product_sub_type else None
                },
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [ "tags", "new_tags", "add_tags", "remove_tags", "removed_tags", "product_sub_type_id"],
            "view_required": [],
            "view_allowed": None,
            "view_forbidden": ["new_tags", "add_tags", "remove_tags", "removed_tags"],
            "no_docs": ["new_tags"]
        }

class DeviceTag(db.Entity, ModelDefinitionMixin):
    name = Required(str, unique=True)
    style = Optional(str)

    devices= Set(Device)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
             "properties": {
                 'id': {
                  "type": "integer",
                            "example": 1234,
                            "value": lambda o: o.id,
                            "description": "This is the ID of the tag."
                        },
                        'name': {
                            "description": "This is the name of the tag. Note that capitalization is ignored for tags.",
                            "oneOf": OPTIONAL_STRING_OPTIONS,
                            "example": "Name",
                            "value": lambda o: o.name
                        },
                        'color': {
                            "description": "This is the color of the tag.",
                            "oneOf": OPTIONAL_STRING_OPTIONS,
                            "example": "teal",
                            "enum": config.COLOR_OPTIONS,
                            "value": lambda o: o.style
                        }
                    },
                    'view_required': [],
                    'view_allowed': [],
                    'edit_required': [],
                    'edit_allowed': ["name", "color"],
                    'create_allowed': [],
                    'create_required': []
                }
