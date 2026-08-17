from datetime import datetime
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from stock_management_system.quantity_stock_models import QuantityStockLocation
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


class Quantity_Stock_Items(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'This table contains the current quantity of each type of quantity-based product in a given location'

    base_model = QuantityStockLocation

    id = PrimaryKey(int, comment="The internal unique ID of the quantity stock item")
    product_sub_type_id = Optional('Product_SubTypes', csv_columns=[("Product Subtype", lambda p: p.name)], comment="The product subtype ID")
    quantity = Optional(float, comment="The current quantity of the product")
    status = Optional(str, comment="The current status of the stock item")
    with_client_id = Optional('Clients', comment="The client ID associated with this stock item")
    with_user_id = Optional('Users', comment="The user ID associated with this stock item")
    in_entity_id = Optional('Operational_Entities', comment="The entity ID where this stock item is located")
    contract_id = Optional('Contracts', comment="The contract ID associated with this stock item")
    addon_id = Optional(int, comment="The add-on ID associated with this stock item")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    # Relationships
    quantity_stock_movements_origin_quantity_stock_item_id = Set('Quantity_Stock_Movements', reverse="origin_quantity_stock_item_id")
    quantity_stock_movements_destination_quantity_stock_item_id = Set('Quantity_Stock_Movements', reverse="destination_quantity_stock_item_id")


    @staticmethod
    def converter(item):
        addon_contract = item.addon.contract.id if item.addon else None
        client_last_contract = item.client.last_contract.id if item.client and item.client.last_contract else None
        contract = addon_contract or client_last_contract

        return {
            "id": item.id,
            "product_sub_type_id": item.product_sub_type.id if item.product_sub_type else None,
            "quantity": item.total_quantity,
            "status": item.status,
            "with_client_id": item.client.id if item.client else None,
            "with_user_id": item.user.id if item.user else None,
            "in_entity_id": item.operational_entity.id if item.operational_entity else None,
            "contract_id": contract,
            "addon_id": item.addon.id if item.addon else None,
            'last_updated': Quantity_Stock_Items.extended_modified_date(item)
        }

    @staticmethod
    def selector(objects):
        return select(item for item in objects).order_by(lambda i: Quantity_Stock_Items.extended_modified_date(i))
    
    @staticmethod
    def extended_modified_date(item):
        return item.modifiedDate



