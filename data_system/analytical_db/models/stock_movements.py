from datetime import datetime
from pony.orm import select
from constants import DEVICE_MODE_NAMES
from payg_loan_system.devices.model.device_mode import DeviceMode
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from stock_management_system.models import StockMovement
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from stock_management_system.stock_status import StockStatus
import config


class Stock_Movements(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Stock movements are individual movements of stock items. '

    base_model = StockMovement

    id = PrimaryKey(int, comment="The internal unique ID of the stock movement")
    stock_item_id = Optional("Stock_Items", comment="The internal ID of the stock item on which the movement is made", column="stock_item_id")
    date = Optional(datetime, comment="The date of the movement")

    origin_status = Optional(str, comment="The status of the stock item before the movement (e.g. with client, with user, etc.)")
    origin_client_id = Optional("Clients", csv_columns=[("Origin Client Name", lambda l: l.full_name)], comment="The internal ID of the client from whom the stock item was taken (if any)", column="origin_client_id")
    origin_user_id = Optional("Users", csv_columns=[("Origin User Name", lambda l: l.full_name)], comment="The internal ID of the user from whom the stock item was taken (if any)", column="origin_user_id")
    origin_entity_id = Optional("Operational_Entities", csv_columns=[("Origin Entity Name", lambda l: l.name)], comment="The internal ID of the entity from which the stock item was taken (if any)", column="origin_entity_id")

    destination_status = Optional(str, comment="The status of the stock item after the movement (e.g. with client, with user, etc.)")
    destination_client_id = Optional("Clients", csv_columns=[("Destination Client Name", lambda l: l.full_name)], comment="The internal ID of the client to whom the stock item was given (if any)", column="destination_client_id")
    destination_user_id = Optional("Users", csv_columns=[("Destination User Name", lambda l: l.full_name)], comment="The internal ID of the user to whom the stock item was given (if any)", column="destination_user_id")
    destination_entity_id = Optional("Operational_Entities", csv_columns=[("Destination Entity Name", lambda l: l.name)], comment="The internal ID of the entity to whom the stock item was given (if any)", column="destination_entity_id")

    status = Optional(str, comment="The approval status the movement, can be accepted, rejected or pending")
    note = Optional(str, comment="A free-form note about the movement")
    receiving_note = Optional(str, comment="A free-form note about why the movement was accepted or rejected")
    product_sub_type = Optional("Product_SubTypes", csv_columns=[("Product SubType Name", lambda p: p.name)], comment="The product subtype id to whom the stock item was given (if any)", column="product_sub_type")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(movement):
        return {
            "id": movement.id,
            "stock_item_id": movement.stock_item.id,
            "date": movement.date,

            "origin_status": movement.origin_status,

            "origin_client_id": movement.origin_client.id if movement.origin_client else None,
            "origin_user_id": movement.origin_user.id if movement.origin_user else None,
            "origin_entity_id": movement.origin_shop.id if movement.origin_shop else None,

            "destination_status": movement.destination_status,

            "destination_client_id": movement.destination_client.id if movement.destination_client else None,
            "destination_user_id": movement.destination_user.id if movement.destination_user else None,
            "destination_entity_id": movement.destination_entity.id if movement.destination_entity else None,

            "status": movement.approval_status or '',
            "note": movement.note or '',
            "receiving_note": movement.receiving_note or '',
            "product_sub_type": movement.product_sub_type.id if movement.product_sub_type else None,
            
            'last_updated': Stock_Movements.extended_modified_date(movement)
        }

    @staticmethod
    def selector(objects):
        return select(move for move in objects if move.previous is not None).order_by(lambda m: Stock_Movements.extended_modified_date(m))
    
    @staticmethod
    def extended_modified_date(item):
        return max(
            item.modifiedDate,
            item.stock_item.modifiedDate,
            item.previous.modifiedDate
        )
