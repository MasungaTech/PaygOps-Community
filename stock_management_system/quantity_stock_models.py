from datetime import datetime

from pony.orm import Optional, Required, Set, composite_key, select

from constants import INTEGER_OPTIONAL_OPTIONS
from core_system.core_entities import db
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.logger.loggers import Error
from stock_management_system.stock_status import (StockMovementStatus,
                                                  StockStatus)


class QuantityStockLocation(db.Entity, ModelDefinitionMixin):

    product_sub_type = Required(
        "ProductSubType", reverse="quantity_stock_locations", column="product_sub_type"
    )
    status = Required(str, py_check=StockStatus.valid)
    user = Optional("User", reverse="quantity_stock_locations", column="user")

    # not used yet
    addon = Optional("ContractAddOn", reverse="quantity_stock_locations", column="addon")

    operational_entity = Optional(
        "HierarchicalOperationalEntity", reverse="quantity_stock_locations", column="entity"
    )
    client = Optional("Client", reverse="quantity_stock_locations", column="client")

    total_quantity = Required(int, py_check=lambda q: q >= 0)

    movements_in = Set("QuantityStockMovement", reverse="destination")
    movements_out = Set("QuantityStockMovement", reverse="origin")

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    composite_key(product_sub_type, status, user, addon, operational_entity)

    @property
    def approved_movements_in(self):
        return self.movements_in.filter(
            lambda m: m.approval_status == StockMovementStatus.accepted
        )

    @property
    def approved_movements_out(self):
        return self.movements_out.filter(
            lambda m: m.approval_status == StockMovementStatus.accepted
        )

    @property
    def pending_movements_out(self):
        return self.movements_out.filter(
            lambda m: m.approval_status == StockMovementStatus.pending
        )

    @property
    def available_total_quantity(self):
        return self.total_quantity - select(
            m.quantity for m in self.pending_movements_out
        ).sum()

    def check_coherence(self):
        if not self.total_quantity == (
            select(m.quantity for m in self.approved_movements_in).sum()
            - select(m.quantity for m in self.approved_movements_out).sum()
        ):
            raise Exception('Total quantity in QuantityStockLocation not coherent')
        if self.product_sub_type.is_serialized:
            raise Exception('Serialized products not allowed for QuantityStockLocation')

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                "product_sub_type_id": {
                    "description": "This is the ID of the product sub type of the stock items",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.product_sub_type.id,
                },
                "status": {
                    "description": "This is a status of the stock items",
                    "type": "string",
                    "example": StockStatus.to_list()[0],
                    "enum": StockStatus.to_list(),
                    "value": lambda o: o.status,
                },
                "user_id": {
                    "description": "This is the ID of the user that has the items (if status is With User)",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.user.id if o.user else None,
                },
                "entity_id": {
                    "description": "This is the ID of the entity that has the items (if statys is In Stock)",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.operational_entity.id if o.operational_entity else None,
                },
                "total_quantity": {
                    "description": "This is the total quantity of stock items in this quantity stock location",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.total_quantity,
                },
            },
            "view_required": [],
            "create_required": ["status"],
            "create_allowed": ["product_sub_type_id", "status", "user_id", "entity_id"],
            "create_forbidden": [],
            "view_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
        }


class QuantityStockMovement(db.Entity, ModelDefinitionMixin):

    date = Required(datetime)
    user = Required("User", reverse="quantity_stock_movements", column="user")
    note = Optional(str)
    receiving_note = Optional(str)
    quantity = Required(int, py_check=lambda q: q >= 0)

    origin = Optional(QuantityStockLocation, column="origin")
    destination = Optional(QuantityStockLocation, column="destination")
    approval_status = Optional(
        str, py_check=StockMovementStatus.valid, index=True, default=StockMovementStatus.accepted
    )

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    def after_insert(self):
        if self.origin:
            if self.quantity > self.origin.available_total_quantity:
                raise ValueError('Not enough items from origin')
            if self.approval_status == StockMovementStatus.accepted:
                self.origin.total_quantity -= self.quantity
            self.origin.check_coherence()
        if self.destination:
            if self.approval_status == StockMovementStatus.accepted:
                self.destination.total_quantity += self.quantity
            self.destination.check_coherence()

    def before_insert(self):
        self.check_coherence()

    def before_update(self):
        self.check_coherence()

    def check_coherence(self):
        if not self.origin and not self.destination:
            raise Error('Movement must have an origin and/or destination')

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "The ID of the quantity stock movement",
                    "example": 12,
                    "value": lambda o: o.id,
                },
                "date": {
                    "description": "This is the date when the movement was done",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.date,
                },
                "user_id": {
                    "description": "This is the ID of the user that made the movement",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.user.id,
                },
                'approval_status': {
                    "description": "Whether the movement has been accepted or rejected",
                    "type": "string",
                    "enum": StockMovementStatus.to_list(),
                    "value": lambda o: o.approval_status
                },
                "note": {
                    "description": "This is a text note to describe the movement",
                    "type": "string",
                    "example": "Example note",
                    "value": lambda o: o.note,
                },
                "quantity": {
                    "description": "This is the quantity of stock items that were moved",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.quantity,
                },
                "product_sub_type_id": {
                    "description": "This is the product sub type ID of stock items that were moved",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.origin.product_sub_type.id if o.origin else o.destination.product_sub_type.id,
                },
                "origin": {**QuantityStockLocation.get_model_schema(op, **kwargs), **{
                    "value": lambda o: o.origin.get_serialized_object() if o.origin else None,
                }},
                "destination": {**QuantityStockLocation.get_model_schema(op, **kwargs), **{
                    "value": lambda o: o.destination.get_serialized_object() if o.destination else None,
                }},
                "origin_status": {
                    "description": "Alternative to 'origin' object - the status of the origin location",
                    "type": "string",
                    "example": StockStatus.to_list()[0],
                    "enum": StockStatus.to_list(),
                    "value": lambda o: o.origin.status if o.origin else None,
                },
                "origin_user_id": {
                    "description": "Alternative to 'origin' object - the user ID for the origin location",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 123,
                    "value": lambda o: o.origin.user.id if o.origin and o.origin.user else None,
                },
                "origin_entity_id": {
                    "description": "Alternative to 'origin' object - the entity ID for the origin location",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 123,
                    "value": lambda o: o.origin.operational_entity.id if o.origin else None,
                },
                "origin_client_id": {
                    "description": "Alternative to 'origin' object - the client ID for the origin location",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 123,
                    "value": lambda o: o.origin.client.id if o.origin and o.origin.client else None,
                },
                "destination_status": {
                    "description": "Alternative to 'destination' object - the status of the destination location",
                    "type": "string",
                    "example": StockStatus.to_list()[0],
                    "enum": [status for status in StockStatus.keys() if status != StockStatus.installed],
                    "value": lambda o: o.destination.status if o.destination else None,
                },
                "destination_user_id": {
                    "description": "Alternative to 'destination' object - the user ID for the destination location",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 123,
                    "value": lambda o: o.destination.user.id if o.destination and o.destination.user else None,
                },
                "destination_entity_id": {
                    "description": "Alternative to 'destination' object - the entity ID for the destination location",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 123,
                    "value": lambda o: o.destination.operational_entity.id if o.destination and o.destination.operational_entity else None,
                },
                "destination_client_id": {
                    "description": "Alternative to 'destination' object - the client ID for the destination location",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 123,
                    "value": lambda o: o.destination.client.id if o.destination and o.destination.client else None,
                },
            },
            "view_required": ["id", "date", "user_id", "quantity", "destination"],
            "create_required": ["product_sub_type_id", "quantity"],
            "create_allowed": [],
            "create_no_docs": ["origin", "destination"],
            "create_forbidden": ["id", "user_id", "date", "destination_client_id"],
            "view_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
        }
