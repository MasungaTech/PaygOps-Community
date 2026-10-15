from datetime import datetime
from decimal import Decimal
from pony.orm import Required, Optional, Set
from core_system.core_entities import db
from shared.helpers.db_helpers import TypeClassBase
from shared.api_helpers.model_definition_base import ModelDefinitionMixin


class MetricFormat(TypeClassBase):
    gps = 'GPS'
    alert = 'Alert'
    string = 'String'
    numeric = 'Numeric'
    boolean = 'Bool'


class MetricType(db.Entity):
    uuid = Required(str)
    name = Required(str)
    credit_unit = Required(str)
    format = Required(str, py_check=MetricFormat.valid)
    metric = Set('Metric')

    def get_serialized_object(self, **kwargs):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'unit': self.credit_unit
        }


class Metric(db.Entity, ModelDefinitionMixin):
    device = Required('Device', column="device")
    metric_type = Required('MetricType', column="metric_type")
    time = Required(datetime)
    value = Optional(float)
    secondary_value = Optional(float)
    text_value = Optional(str)

    @property
    def modifiedDate(self):
        return self.time

    def get_display_value(self):
        if self.metric_type.format == MetricFormat.string:
            return self.text_value
        if self.metric_type.format == MetricFormat.numeric:
            return round(self.value, 2) if self.value else 0
        if self.metric_type.format == MetricFormat.boolean:
            return True if self.value == 1 else False
        return None
    
    @classmethod
    def get_model_definition(cls, op, include_objects=None, special_data=None, **kwargs):
        data = {
            "properties": {
                'id': {
                    "description": "The ID of the Metric",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.id
                },
                'device_serial_number': {
                    "description": "The serial number of the device on which the metric is",
                    "type": "string",
                    "example": "SOL-1234",
                    "value": lambda o: o.device.composed_serial
                },
                'date': {
                    "description": "The datetime of the metric",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime(1980, 6, 15).isoformat(),
                    "value": lambda o: o.time
                },
                'name': {
                    "description": "The name of the metric",
                    "type": "string",
                    "example": "Instant Power",
                    "value": lambda o: o.metric_type.name
                },
                'unit': {
                    "description": "The unit of the metric",
                    "type": "string",
                    "example": "Ampere",
                    "value": lambda o: o.metric_type.credit_unit
                },
                'format': {
                    "description": "The format of the metric",
                    "type": "string",
                    "enum": [
                        MetricFormat.gps,
                        MetricFormat.alert,
                        MetricFormat.string,
                        MetricFormat.numeric
                    ],
                    "example": "Numeric",
                    "value": lambda o: o.metric_type.format
                },
                'value_text': {
                    "description": "The value of the metric in text form",
                    "type": "string",
                    "example": "Tampered",
                    "value": lambda o: o.value_text if o.metric_type.format == MetricFormat.string else None
                },
                'value_numeric': {
                    "description": "The value of the metric if it's numeric",
                    "type": "number",
                    "example": 12.3,
                    "value": lambda o: o.value if o.metric_type.format == MetricFormat.numeric else None
                },
                'value_gps_longitude': {
                    "description": "The value of the metric if it's numeric",
                    "type": "number",
                    "example": 12.3,
                    "value": lambda o: o.value if o.metric_type.format == MetricFormat.gps else None
                },
                'value_gps_latitude': {
                    "description": "The value of the metric if it's numeric",
                    "type": "number",
                    "example": 12.3,
                    "value": lambda o: o.secondary_value if o.metric_type.format == MetricFormat.gps else None
                }
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': [],
            'create_allowed': [],
            'create_required': []
        }
        return data
