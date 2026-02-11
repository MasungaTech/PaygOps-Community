from pony import orm
from core_system.core_entities import db
from datetime import datetime
from shared.api_helpers.model_definition_base import ModelDefinitionMixin


class DeviceNote(db.Entity, ModelDefinitionMixin):

    content = orm.Required(str)
    time = orm.Required(datetime)
    user = orm.Required('User')
    device = orm.Required('Device')

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "The unique ID of the note"
                },
                'content': {
                    "type": "string",
                    "example": 'This is a note',
                    "value": lambda o: o.content,
                    "description": "The content of the note."
                },
                'date': {
                    "description": "The date and time at which the note was made in ISO format.",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime(2020, 6, 15).isoformat(),
                    "value": lambda o: o.time
                },
                'user_id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.user.id,
                    "description": "The ID of the user making the note."
                },
                'device_serial_number': {
                    "type": "string",
                    "example": "SOL-1234",
                    "value": lambda o: o.device.composed_serial,
                    "description": "The serial number of the device to which the note is attached to"
                },
            },
            "create_required": ["content"], # device is pass via path, not in data 
            "create_allowed": [],
            "create_forbidden": ["date", "id", "user_id"],
            "edit_required": [],
            "edit_allowed": ["content"],
            "view_required": [],
            "view_allowed": None
        }
