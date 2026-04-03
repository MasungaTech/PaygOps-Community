from datetime import datetime
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from stock_management_system.quantity_stock_models import QuantityStockMovement
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


class Quantity_Stock_Movements(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'This table tracks the movement history of quantity-based stock items between locations and statuses'

    base_model = QuantityStockMovement

    id = PrimaryKey(int, comment="The internal unique ID of the quantity stock movement record")
    product_sub_type_id = Optional('Product_SubTypes', csv_columns=[("Product Subtype", lambda p: p.name)], comment="The product subtype ID for the stock item being moved")
    quantity = Optional(int, comment="The quantity of stock items being moved")
    date = Optional(datetime, comment="The date and time when the movement occurred")
    origin_quantity_stock_item_id = Optional('Quantity_Stock_Items', comment="The ID of the source stock item from which the movement originated")
    origin_status = Optional(str, comment="The status of the stock item at the origin location before movement")
    origin_client_id = Optional('Clients', csv_columns=[("Clients", lambda c: c.name)], comment="The client ID associated with the stock item at the origin location")
    origin_user_id = Optional('Users', csv_columns=[("Users", lambda u: u.name)], comment="The user ID associated with the stock item at the origin location")
    origin_entity_id = Optional('Operational_Entities', csv_columns=[("Operational_Entities", lambda e: e.name)], comment="The entity ID where the stock item was located before movement")
    destination_quantity_stock_item_id = Optional('Quantity_Stock_Items', comment="The ID of the destination stock item where the movement is directed")
    destination_status = Optional(str, comment="The status of the stock item at the destination location after movement")
    destination_client_id = Optional('Clients', csv_columns=[("Clients", lambda c: c.name)], comment="The client ID associated with the stock item at the destination location")
    destination_user_id = Optional('Users', csv_columns=[("Users", lambda u: u.name)], comment="The user ID associated with the stock item at the destination location")
    destination_entity_id = Optional('Operational_Entities', csv_columns=[("Operational_Entities", lambda e: e.name)], comment="The entity ID where the stock item is located after movement")
    status = Optional(str, comment="The current status of the movement record (e.g., pending, completed, cancelled)")
    notes = Optional(str, comment="General notes about the stock movement")
    receiving_notes = Optional(str, comment="Notes specific to the receiving process of the stock movement")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(item):
        stock_location = item.origin or item.destination

        return {
            "id": item.id,
            "product_sub_type_id": stock_location.product_sub_type.id if stock_location else None,
            "quantity": item.quantity,
            "date": item.date,
            "origin_quantity_stock_item_id": item.origin.id if item.origin else None,
            "origin_status": item.origin.status if item.origin else None,
            "origin_client_id": item.origin.client.id if item.origin and item.origin.client else None,
            "origin_user_id": item.origin.user.id if item.origin and item.origin.user else None,
            "origin_entity_id": item.origin.operational_entity.id if item.origin and item.origin.operational_entity else None,
            "destination_quantity_stock_item_id": item.destination.id if item.destination else None,
            "destination_status": item.destination.status if item.destination else None,
            "destination_client_id": item.destination.client.id if item.destination and item.destination.client else None,
            "destination_user_id": item.destination.user.id if item.destination and item.destination.user else None,
            "destination_entity_id": item.destination.operational_entity.id if item.destination and item.destination.operational_entity else None,
            "status": item.approval_status,
            "notes": item.note,
            "receiving_notes": item.receiving_note,
            'last_updated': Quantity_Stock_Movements.extended_modified_date(item)
        }

    @staticmethod
    def selector(objects):
        return select(item for item in objects).order_by(lambda i: Quantity_Stock_Movements.extended_modified_date(i))
    
    @staticmethod
    def extended_modified_date(item):
        return item.modifiedDate



