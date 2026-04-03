from pony.orm import *
from core_system.core_entities import db
from datetime import datetime
import os
import config
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.helpers.db_helpers import TypeClassBase


class StoredFile(db.Entity, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    uuid = Required(str, index=True, unique=True)
    type = Required(str, index=True) # 'picture' or 'file'
    available = Required(bool) # Whether it's synced on the server or not
    original_filename = Optional(str)
    filename = Required(str)
    thumbnail_filename = Optional(str)
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True) # For MobileAPI
    picture_gpslon = Optional(float)
    picture_gpslat = Optional(float)
    backup_time = Optional(datetime, index=True)

    # FK
    person = Optional('Person', column='person')
    answers = Set('Answer')

    def get_file_path(self):
        if self.type == StoredFileType.PICTURE:
            return os.path.join(config.CONTENT_PATH+'pictures', self.filename)
        else:
            return os.path.join(config.CONTENT_PATH+'files', self.filename)

    def get_thumbnail_path(self):
        if self.thumbnail_filename:
            return os.path.join(config.CONTENT_PATH+'pictures', self.thumbnail_filename)

    def is_found(self):
        if os.path.isfile(self.get_file_path()):
            return True
        return False

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'uuid': {
                    "type": "string",
                    "example": "217963fe-aa20-4a78-8eb9-e4c5c747e3e2",
                    "value": lambda o: o.uuid,
                    "description": "This is the UUID of the file."
                },
                'type': {
                    "type": "string",
                    "example": 'picture',
                    "enum": StoredFileType.to_list(),
                    "value": lambda o: o.type,
                    "description": "This is the type of the file."
                },
            },
            "create_required": [],
            "create_allowed": [],
            "create_forbidden": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }

class StoredFileType(TypeClassBase):
    PICTURE = 'picture'
    FILE = 'file'
