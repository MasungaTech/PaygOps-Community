from datetime import datetime
import json
from pony.orm import select, Set, Json
from constants import DEVICE_MODE_NAMES
from payg_loan_system.devices.model.device_mode import DeviceMode
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from shared.api_helpers.server_helpers.json_serialization import CustomJSONEncoder
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from stock_management_system.models import StockItem
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from stock_management_system.stock_status import StockStatus
import config


class Stock_Items(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Stock items are individual items that are tracked in the stock management system. '

    base_model = StockItem

    id = PrimaryKey(int, comment="The internal unique ID of the stock item")
    serial_number = Optional(str, comment="The serial number of the stock item (if any)")
    type = Optional(str, comment="The type of the device (e.g. SunQueen, Solaris, etc.)")
    status = Optional(str, comment="The status of the stock item (e.g. in stock, with user, etc.)")

    with_client_id = Optional("Clients", csv_columns=[("With Client Name", lambda l: l.full_name)], comment="The internal ID of the client who has the stock item (if any)", column="with_client_id")
    with_user_id = Optional("Users", csv_columns=[("With User Name", lambda l: l.full_name)], comment="The internal ID of the user who has the stock item (if any)", column="with_user_id")
    in_entity_id = Optional("Operational_Entities", csv_columns=[("In Entity Name", lambda l: l.name)], comment="The internal ID of the entity where the stock item is located (if any)", column="in_entity_id")
    contract_id = Optional("Contracts", comment="The internal ID of the contract that the stock item is associated with (if any)", column="contract_id")
    addon_id = Optional(int, comment="The internal ID of the add-on that the stock item is associated with (if any)", column="addon_id")

    paygo_active_until = Optional(datetime, comment="The date at which the stock item will turn off (for PAYGO items)")
    paygo_mode = Optional(str, comment="Whether the item is fully unlocked or in PAYGO mode (for PAYGO items)")

    # Virtual (not in table)
    movements = Set("Stock_Movements")

    # Internal
    last_updated = Optional(datetime)

    tags = Optional(str, comment="The comma-separated list of tags associated with the device")
    notes = Optional(Json, comment="Notes on the device in Json format")
    product_sub_type_id = Optional("Product_SubTypes", csv_columns=[("Product Sub Type Name", lambda pst: pst.name)], comment="The internal ID of the product sub-type of the stock item, if applicable")
    addons = Set("AddOns")
    metrics = Set("Device_Metrics")
    if config.ENABLE_ENTERPRISE_FEATURES:
        tasks = Set("Tasks")

    @staticmethod
    def converter(item):
        device_contract = item.device.contract.id if item.device.contract else None
        client_last_contract = item.client.last_contract.id if item.client and item.client.last_contract else None
        contract = device_contract or client_last_contract

        return {
            "id": item.id,
            "serial_number": item.device.composed_serial,
            "type": item.device.type,
            "status": StockStatus.to_human(item.status if item.last_movement else 'orphaned'),

            "with_client_id": item.client.id if item.last_movement and item.client else None,
            "with_user_id": item.user.id if item.last_movement and item.user else None,
            "in_entity_id": item.shop.id if item.last_movement and item.shop else None,

            "paygo_active_until": item.device.ActiveUntil if item.device.Mode == DeviceMode.time else None,
            "paygo_mode": DEVICE_MODE_NAMES.get(item.device.Mode) or '',
            
            "contract_id": contract,
            "addon_id": item.device.addon.id if item.device.addon else None,
            
            'last_updated': Stock_Items.extended_modified_date(item),

            "tags": ",".join([t.name for t in item.device.tags]),
            "notes": json.dumps([n.get_serialized_object() for n in item.device.notes.select()], cls=CustomJSONEncoder),
            
            "product_sub_type_id": item.device.product_sub_type.id if item.device.product_sub_type else None

        }

    @staticmethod
    def selector(objects):
        return select(item for item in objects).order_by(lambda i: Stock_Items.extended_modified_date(i)).prefetch(StockItem.device, StockItem.last_movement)
    
    @staticmethod
    def extended_modified_date(item):
        return max(
            item.modifiedDate,
            item.device.modifiedDate
        )


class Product_SubTypes(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Product sub-types are different models or vairants of devices with in a product type'

    base_model = ProductSubType
    
    id = PrimaryKey(int, comment="The unique ID for the product sub-type")
    name = Optional(str, comment="The name of the product sub-type")
    device_type = Optional(str, comment="The device type to which product sub-type belongs to")
    sku = Optional(str, comment="SKU for the product sub-type")
    is_serialized = Optional(bool, comment="Serialized state for the product sub-type")
    
    # Relationships
    stock_items = Set("Stock_Items")
    stock_movements = Set("Stock_Movements")
    quantity_stock_items = Set("Quantity_Stock_Items", reverse="product_sub_type_id")
    quantity_stock_movements = Set("Quantity_Stock_Movements", reverse="product_sub_type_id")

    # Internal
    last_updated = Optional(datetime)

    @staticmethod
    def converter(pst):
        return {
            "id": pst.id,
            "name": pst.name,
            "device_type": pst.device_type,
            "sku": pst.sku if pst.sku else '',
            "is_serialized": pst.is_serialized,
            'last_updated': pst.modifiedDate,
        }

    @staticmethod
    def selector(objects):
        return select(pst for pst in objects).order_by(lambda i: i.modifiedDate)
    