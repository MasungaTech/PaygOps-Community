
import config
import json
from datetime import datetime
from pony.orm import select, Json, Set
from shared.api_helpers.server_helpers.json_serialization import CustomJSONEncoder
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from task_system.models.task_category import TaskCategory


class Task_Types(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Task types are used to quickly create tasks based on a template and categorise them for analysis.'

    base_model = TaskCategory

    id = PrimaryKey(int, comment="The internal unique ID of the Task type")
    name = Optional(str, comment="The name of Task type")
    default_task_name = Optional(str, comment="The default name of Task type")
    default_task_instructions = Optional(str, comment="The default instruction of Task type, they are displayed in a task in a Task type incase instructions are not provided")  # Default Task Instructions (text)
    created_date = Optional(datetime, comment="The date at which the Task type was created")
    modified_date = Optional(datetime, comment="The date at which the Task type was modified")
    linked_objects = Optional(Json, comment="The objects linked to the Task Type (eg. client, lead, etc.)")
    tasks = Set('Tasks')

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(task_type):
        return {
            "id": task_type[0],
            "name": task_type[1],
            "default_task_name": task_type[2],
            "default_task_instructions": task_type[3],
            "created_date": task_type[4],
            "modified_date": task_type[5],
            "linked_objects": json.dumps(task_type[6], cls=CustomJSONEncoder),
            "last_updated": task_type[5]
        }

    @staticmethod
    def selector(objects):
        return select((
            tt.id,
            tt.name,
            tt.default_task_name,
            tt.default_task_instructions,
            tt.created_date,
            tt.modified_date,
            tt.linked_objects,
            Task_Types.extended_modified_date(tt)
        ) for tt in objects).order_by(8)

    @staticmethod
    def extended_modified_date(obj):
        return obj.modified_date