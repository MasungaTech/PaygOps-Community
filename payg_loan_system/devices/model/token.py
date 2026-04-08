from datetime import datetime
from decimal import Decimal
from pony.orm import Required, Optional, Set
from pony import orm
from core_system.core_entities import db
from shared.services.sorter import Sorter
from shared.api_helpers.model_definition_base import ModelDefinitionMixin


class Token(db.Entity, ModelDefinitionMixin):
    time = Required(datetime)
    uuid = Required(str)
    device = Required("Device", column="device")
    request_code = Optional(str)
    token = Required(str)
    sync_scope = Optional(int)
    mode = Optional(int)
    expiration_time = Optional(datetime)
    credit_value = Optional(Decimal)
    credit_unit = Optional(str)
    token_count = Optional(int)
    token_type = Optional(str)
    repayments = Set("ContractRepayment")

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                "time": {
                    "type": "string",
                    "format": "date-time",
                    "example": datetime(2020, 6, 15).isoformat(),
                    "description": "The time at which the token was generated. ",
                    "value": lambda o: o.time
                },
                "uuid": {
                    "type": "string",
                    "format": "uuid",
                    "example": "xxxxxxx-yyyyyyy-zzzzzzz",
                    "description": "The UUID of the token. ",
                    "value": lambda o: o.uuid
                },
                "device": {
                    "type": "string",
                    "example": "SOL-1234",
                    "description": "The serial_number of the device. It must contain the type prefix. ",
                    "value": lambda o: o.device.composed_serial
                },
                "request_code": {
                    "type": "string",
                    "example": "X1234CB",
                    "description": "The request code provided by the user to get the token (for two-way code devices only). ",
                    "value": lambda o: o.request_code
                },
                "token": {
                    "type": "string",
                    "example": "111 222 333",
                    "description": "The token itself. ",
                    "value": lambda o: o.token
                },
                "sync_scope": {
                    "type": "integer",
                    "example": 1,
                    "description": "The scope of the sync. 1: Device, 2: Panel, 3: Battery, 4: Payg Mode",
                    "value": lambda o: o.sync_scope
                },
                "mode": {
                    "type": "integer",
                    "example": 1,
                    "description": "The mode of the device. 1: Time, 2: Credit, 3: Disabled",
                    "value": lambda o: o.mode
                },
                "expiration_time": {
                    "type": "string",
                    "format": "date-time",
                    "example": datetime(2020, 6, 22).isoformat(),
                    "description": "The target time at which the device will switch off after applying the token. ",
                    "value": lambda o: o.expiration_time
                },
                "credit_value": {
                    "type": "integer",
                    "example": 7,
                    "description": "The number of credits given. ",
                    "value": lambda o: o.credit_value
                },
                "credit_unit": {
                    "type": "string",
                    "example": "Liters",
                    "description": "The units of the credits given (default: Days). ",
                    "value": lambda o: o.credit_unit
                },
                "token_count": {
                    "type": "integer",
                    "example": 1,
                    "description": "The number of tokens generated. ",
                    "value": lambda o: o.token_count
                },
                "token_type": {
                    "type": "string",
                    "example": "ADD_CREDIT",
                    "description": "The type of the token. ADD_CREDIT: Add credit, SET_CREDIT: Set credit, DISABLE_PAYG: Disable PAYG",
                    "value": lambda o: o.token_type
                },
                "repayments": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                    },
                    "value": lambda o: [r.id for r in o.repayments]
                }
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }


class TokenSorter(Sorter):

    @classmethod
    def real_field_sort(cls, field_name, desc=False):
        options = {
            'uuid': Token.uuid,
            'time': Token.time,
            'request_code': Token.request_code,
            'client': lambda t: t.device.contract.client.full_name,
            'device': lambda t: t.device.composed_serial,
            'token_type': Token.token_type,
            'credit_value': lambda t: t.credit_value or t.expiration_time
        }
        options_desc = {
            'client': lambda t: orm.desc(t.device.contract.client.full_name),
            'device': lambda t: orm.desc(t.device.composed_serial),
            'credit_value': lambda t: orm.desc(t.credit_value or t.expiration_time)
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, orm.desc(Token.time)))
        return options.get(field_name, orm.desc(Token.time))
