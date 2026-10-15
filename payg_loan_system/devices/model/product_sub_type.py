from datetime import datetime
from pony.orm import Required, Optional, Set, composite_key
from constants import OPTIONAL_STRING_OPTIONS
from core_system.core_entities import db
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from stock_management_system.quantity_stock_models import QuantityStockLocation
from stock_management_system.models import StockMovement

class ProductSubType(db.Entity, ModelDefinitionMixin):
    name = Required(str)
    sku = Optional(str, unique=True, nullable=True)
    device_type = Required(str)
    is_serialized = Required(bool, default=True)

    devices = Set('Device')
    offers = Set('Offer')
    addon_offers = Set('AddOnOffer')
    quantity_stock_locations = Set(QuantityStockLocation)
    stock_movements = Set(StockMovement)

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    composite_key(device_type, name)

    def after_update(self):
        now = datetime.now()
        for device in self.devices:
            device.modifiedDate = now

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "The unique ID of the product sub-type"
                },
                'name': {
                    "type": "string",
                    "example": 'Product Name',
                    "value": lambda o: o.name,
                    "description": "The name of the product sub-type, must be unique."
                },
                'sku': {
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": '1234',
                    "value": lambda o: o.sku,
                    "description": "The unique SKU of the product."
                },
                'device_type': {
                    "type": "string",
                    "example": 'OPG',
                    "value": lambda o: o.device_type,
                    "description": "The decice type of the product sub-type."
                },
                'is_serialized': {
                    "type": "boolean",
                    "example": False,
                    "value": lambda o: o.is_serialized,
                    "description": "Indicates if the product sub-type is serialized (default `true`). Serialized products have unique serial number for each item, while non-serialized products are tracked purely by quantity."
            },
            },
            "create_required": ["name", "device_type"],
            "create_allowed": [],
            "create_forbidden": ["id"],
            "edit_required": [],
            "edit_allowed": ["name", "sku", "device_type", "is_serialized"],
            "view_required": [],
            "view_allowed": None
        }
