from datetime import datetime

from pony.orm import Optional, Required, Set

from constants import EMPTY_STRING_OPTION, INTEGER_OPTIONAL_OPTIONS, INTEGER_REQUIRED_OPTIONS, OPTIONAL_STRING_OPTIONS
from core_system.core_entities import db
from shared.api_helpers.client_helpers.uuid_generation_helpers import \
    generate_uuid
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.services.celery_queue_service import CeleryQueueService
from stock_management_system.stock_status import (StockMovementStatus,
                                                  StockStatus)
from worker_app.tasks.generate_offline_tokens import \
    refresh_offline_tokens_for_device


class StockItem(db.Entity, ModelDefinitionMixin):
    device = Optional('Device')
    last_movement = Optional('StockMovement', column="last_movement")
    movements = Set('StockMovement')
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = Optional(str, unique=True)
    
    @property
    def composed_serial(self):
        return self.device.composed_serial

    @property
    def status(self):
        return self.last_movement.destination_status

    @property
    def user(self):
        return self.last_movement.destination_user

    @property
    def client(self):
        return self.last_movement.destination_client

    @property
    def shop(self):
        return self.last_movement.destination_entity

    @property
    def reserved(self):
        return (
            self.last_movement and
            self.last_movement.approval_status == StockMovementStatus.pending
        )

    def before_insert(self):
        if self.last_movement:
            raise Exception('last_movement is a restricted property')
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    @classmethod
    def get_model_definition(cls, **kwargs):
        return {
            "properties": {
                'id': {
                    "value": lambda o: o.id,
                    "description": "The unique ID of the Stock Item",
                    "example": 123,
                    "type": "integer",
                },
                'device': {
                    "value": lambda o: o.device.composed_serial,
                    "description": "The serial number of the devices associated to the stock item",
                    "type": "string",
                    "example": "NPG-1324"
                },
                'movements': {
                    "value": lambda o: [m.id for m in o.movements if m.previous],
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "example": [12, 13, 14],
                    "description": "List of IDs of movements of the stock item"
                },
                'status': {
                    "value": lambda o: o.status,
                    "enum": StockStatus.to_list(),
                    "type": "string",
                    "example": StockStatus.orphaned,
                    "description": "Current status of the stock item (type of location)"
                },
                'user': {
                    "value": lambda o: o.user.id if o.user else None,
                    "example": 123,
                    "type": "integer",
                    "description": "User in possession of the stock item (if with_user)"
                },
                'client': {
                    "value": lambda o: o.client.id if o.client else None,
                    "example": 123,
                    "type": "integer",
                    "description": "Client in possession of the stock item (if installed)"
                },
                'shop': {
                    "value": lambda o: o.shop.not_empty_code if o.shop else None,
                    "example": 123,
                    "deprecated": True,
                    "type": "integer",
                    "description": "Hub in possession of the stock item (if in_stock)"
                },
                'entity': {
                    "value": lambda o: o.shop.id if o.shop else None,
                    "example": 123,
                    "type": "integer",
                    "description": "Entity in possession of the stock item (if in_stock)"
                }
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }
    
    def before_update(self):
        self.modifiedDate = datetime.now()

    def after_update(self):
        if self.device:
            self.device.update_cached_data()
            CeleryQueueService.execute_task(refresh_offline_tokens_for_device, self.device.id)

class StockMovement(db.Entity, ModelDefinitionMixin):
    stock_item = Required(StockItem, column="stock_item")
    date = Required(datetime)
    user = Optional('User', reverse='stock_movements', column="user")
    note = Optional(str)
    receiving_note = Optional(str)
    destination_status = Required(str, py_check=StockStatus.valid, index=True)
    destination_user = Optional('User', reverse='destined_stock', column="destination_user")
    destination_client = Optional('Client', reverse='destined_stock', column="destination_client")
    destination_entity = Optional('HierarchicalOperationalEntity', reverse='destined_stock')
    previous = Optional('StockMovement', reverse='next', column="previous")
    next = Set('StockMovement', reverse='previous') # there could be more than one of rejections
    last_movement_of = Optional(StockItem, reverse='last_movement')
    approval_status = Optional(
        str, py_check=StockMovementStatus.valid, index=True, default=StockMovementStatus.accepted)
    mobile_uuid = Optional(str, unique=True)
    quantity = Optional(int)
    product_sub_type = Optional("ProductSubType")

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    # RAW_RESPONSE = True

    @property
    def origin_status(self):
        return self.previous.destination_status

    @property
    def origin_user(self):
        return self.previous.destination_user

    @property
    def origin_client(self):
        return self.previous.destination_client

    @property
    def origin_shop(self):
        return self.previous.destination_entity

    def before_insert(self):
        self._check_data_coherence()
        if self.previous:
            raise Exception('previous is a restricted property')
        if self.stock_item.last_movement:
            if self.stock_item.last_movement.date > self.date:
                raise Exception(
                    'Movement date has to be later in time than stock item last movement date')
            self.previous = self.stock_item.last_movement
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    def before_update(self):
        self._check_data_coherence()
        if self.previous and self.previous.date > self.date:
            raise Exception('Date cannot be earlier in time than previous movement')
        self.modifiedDate = datetime.now()

    def after_insert(self):
        self.stock_item.last_movement = self

    def _check_data_coherence(self):
        if not StockStatus.valid(self.destination_status):
            raise Exception('INVALID_DESTINATION_STATUS')
        if (self.destination_status in [StockStatus.orphaned, StockStatus.lost] and
                (self.destination_user is not None or self.destination_client is not None or
                 self.destination_entity is not None)):
            raise Exception('STATUS_LOCATION_INCOHERENCE')
        if (self.destination_status == StockStatus.in_stock and
                (self.destination_user is not None or self.destination_client is not None or
                 self.destination_entity is None)):
            raise Exception('STATUS_LOCATION_INCOHERENCE')
        if (self.destination_status == StockStatus.with_user and
                (self.destination_user is None or self.destination_client is not None or
                 self.destination_entity is not None)):
            raise Exception('STATUS_LOCATION_INCOHERENCE')
        if (self.destination_status == StockStatus.installed and
                (self.destination_user is not None or self.destination_client is None or
                 self.destination_entity is not None)):
            raise Exception('STATUS_LOCATION_INCOHERENCE')

    @classmethod
    def get_model_definition(cls, **kwargs): # do this with a discriminator schema?
        return {
            "properties": {
                'id': {
                    "description": "Id number of the stock item",
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id
                },
                'stock_item_id': {
                    "description": "The ID of the stock item that the movement makes reference to. ",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 1234,
                    "value": lambda o: o.stock_item.id
                },
                'stock_item_ids': {
                    "description": "The array of IDs of the stock items that the movement makes reference to. ",
                    "type": "array",
                    "items": {
                        "oneOf": INTEGER_OPTIONAL_OPTIONS
                    },
                    "example": [1234, 4567],
                    "value": lambda o: [o.stock_item.id]
                },
                'serial_number': {
                    "description": "The full device serial number of the stock item that the movement makes reference to. ",
                    "type": "string",
                    "example": "NPG-1234",
                    "value": lambda o: o.stock_item.device.composed_serial
                },
                'date': {
                    "description": "This is the date when the movement was done",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.date
                },
                'user_id': {
                    "description": "The Id number of the user who performed the movement (if any)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 1234,
                    "value": lambda o: o.user.id if o.user else None
                },
                'note': {
                    "description": "A note providing more information about the movement",
                    "type": "string",
                    "example": "Example note",
                    "value": lambda o: o.note
                },
                'receiving_note': {
                    "description": "A note about why the movement was rejected or accepted",
                    "type": "string",
                    "example": "Example note",
                    "value": lambda o: o.receiving_note
                },
                'destination_status': {
                    "description": "The destination status of the stock item",
                    "type": "string",
                    "enum": list(StockStatus.keys()),
                    "value": lambda o: o.destination_status
                },
                'destination_user_id': {
                    "description": "The Id number of the user to whom the stock item was moved (if `destination_status` is “with_user”)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "value": lambda o: o.destination_user.id if o.destination_user else None
                },
                'destination_client_id': {
                    "description": "The Id number of the client to whom the stock item was moved (if `destination_status` is “installed”)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "value": lambda o: o.destination_client.id if o.destination_client else None
                },
                'destination_hub_id': {
                    "description": "The Id number of the hub to which the stock item was moved (if `destination_status` is “in_stock”)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "deprecated": True,
                    "value": lambda o: o.destination_entity.not_empty_code if o.destination_entity else None
                },
                'destination_entity_id': {
                    "description": "The Id number of the Entity to which the stock item was moved (if `destination_status` is “in_stock”)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "value": lambda o: o.destination_entity.id if o.destination_entity else None
                },
                'origin_status': {
                    "description": "The origin status of the stock item",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "enum": list(StockStatus.keys()),
                    "value": lambda o: o.origin_status if o.previous else None
                },
                'origin_user_id': {
                    "description": "The Id number of the user to whom the stock item was moved (if `origin_status` is “with_user”)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "value": lambda o: o.origin_user.id if o.previous and o.origin_user else None
                },
                'origin_client_id': {
                    "description": "The Id number of the client to whom the stock item was moved (if `origin_status` is “installed”)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "value": lambda o: o.origin_client.id if o.previous and o.origin_client else None
                },
                'origin_hub': {
                    "description": "The Id number of the hub to which the stock item was moved (if `origin_status` is “in_stock”)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "deprecated": True,
                    "example": 12,
                    "value": lambda o: o.origin_shop.not_empty_code if o.previous and o.origin_shop else None
                },
                'origin_entity_id': {
                    "description": "The Id number of the hub to which the stock item was moved (if `origin_status` is “in_stock”)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 12,
                    "value": lambda o: o.origin_shop.id if o.previous and o.origin_shop else None
                },
                'approval_status': {
                    "description": "Whether the movement has been accepted or rejected",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "enum": StockMovementStatus.to_list(),
                    "value": lambda o: o.approval_status
                },
                'quantity': {
                    "description": "The quantity of the moved stock item",
                    "type": "integer",
                    "example": 5,
                    "value": lambda o: o.quantity
                },
                'product_sub_type': {
                    "description": "The sub type ID of the moved stock item",
                    "oneOf": OPTIONAL_STRING_OPTIONS,
                    "example": "",
                    "value": lambda o: o.product_sub_type.id if o.product_sub_type else None
                }
            },
            "create_required": [],
            "create_allowed": [
                'stock_item_id', 'note', 'destination_status', 'serial_number',
                'destination_user_id', 'destination_entity_id', 'stock_item_ids'
            ],
            "edit_required": [],
            "edit_allowed": ['note','stock_item_id','stock_item_ids', 'destination_status', 'serial_number',
                'destination_user_id', 'destination_entity_id'],
            "view_required": [],
            "view_forbidden": ['stock_item_ids'],
            "view_allowed": None
        }
