import config
import json
from datetime import datetime
from pony.orm import select
from payg_loan_system.devices.model.device_metrics_model import Metric
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from task_system.models.task import Task


class Tasks(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'A Task contains essential information for organizing, monitoring, and overseeing work assignments.'

    base_model = Task

    id = PrimaryKey(int, comment="The internal unique ID of the Task")
    task_name = Optional(str, comment="The name of Task")
    type = Optional('Task_Types', csv_columns=[("Task Type Name", lambda t: t.name)], comment="The internal ID of the type of the Task", column="type")
    notes = Optional(str, comment="The notes providing information from the Task assignee")
    instructions = Optional(str, comment="The instruction providing information from the Task creator")
    deadline = Optional(datetime, comment="The date at which the Task is due")
    created_date = Optional(datetime, comment="The date at which the Task was created")
    started_time = Optional(datetime, comment="The date at which the Task was started")
    completion_date = Optional(datetime, comment="The date at which the Task was completed")
    status = Optional(str, comment="The current status of the Task")
    creator_user_id = Optional("Users", csv_columns=[("Creator Name", lambda c: c.full_name)], comment="The id of the User who created the Task", column="creator_user_id")
    assignee_user_id = Optional("Users", csv_columns=[("Assignee Name", lambda a: a.full_name)], comment="The id of the User who was assigned the Task", column="assignee_user_id")
    client_id = Optional("Clients", csv_columns=[("Client Name", lambda c: c.full_name)], comment="The id of the Client who was linked to the Task", column="client_id")
    lead_id = Optional("Leads", csv_columns=[("Lead Name", lambda l: l.full_name)], comment="The id of the Lead who was linked to the Task", column="lead_id")
    stock_item_id = Optional("Stock_Items", csv_columns=[("Device Serial Number", lambda dm: dm.serial_number)], comment="The id of the Stock Item which was linked to the Task", column="stock_item_id")
    contract_id = Optional("Contracts", csv_columns=[("Contract Reference", lambda c: c.reference)], comment="The id of the Contract which was linked to the Task", column="contract_id")


    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(task):
        return {
            "id": task[0],
            "task_name": task[1].formatted_name(),
            "type": task[2].id if task[2] else None,
            "notes": task[3],
            "instructions": task[1].formatted_instructions(),
            "deadline": task[5],
            "created_date": task[6],
            "started_time": task[7],
            "completion_date": task[8],
            "status": task[9],
            "creator_user_id": task[10].id if task[10] else None,
            "assignee_user_id": task[11].id if task[11] else None,
            "client_id": task[12].id if task[12] else None,
            "lead_id": task[13].id if task[13] else None,
            "stock_item_id": task[14].id if task[14] else None,
            "contract_id": task[15].id if task[15] else None,
            "last_updated": task[16]
        }

    @staticmethod
    def selector(objects):
        return select((
            t.id,
            t,
            t.task_category,
            t.notes,
            t.instructions,
            t.deadline,
            t.created_date,
            t.started_time,
            t.completion_date,
            t.status,
            t.creator,
            t.assignee,
            t.client,
            t.lead,
            t.device,
            t.contract,
            Tasks.extended_modified_date(t)
        ) for t in objects).order_by(16)

    @staticmethod
    def extended_modified_date(obj):
        return obj.modified_date