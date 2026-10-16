from datetime import datetime
from pony.orm import select, group_concat, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config

ENTERPRISE_FEATURES_ENABLED = getattr(config, "ENABLE_ENTERPRISE_FEATURES", False)

if ENTERPRISE_FEATURES_ENABLED:
    from after_sales_system.issue_system.model.issue_model import Issue, IssueStatus, IssuePriority
else:
    # Stub classes for when enterprise features are disabled
    class Issue:
        pass
    class IssueStatus:
        @staticmethod
        def to_human(_):
            return 'not_available'
    class IssuePriority:
        @staticmethod
        def to_human(_):
            return 'not_available'


class Issues(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Issues are reports of issues experienced by client and used to track their resolution. '

    base_model = Issue

    id = PrimaryKey(int, comment="The internal unique ID of the issue")
    type = Optional(str, comment="The type of issue (e.g. payment issue, battery issue, etc.)")
    priority = Optional(str, comment="The priority of the issue (e.g. high, medium, low)")
    status = Optional(str, comment="The status of the issue (e.g. new, solved, etc.)")
    start_date = Optional(datetime, comment="The date at which the issue was reported")
    end_date = Optional(datetime, comment="The date at which the issue was closed")
    days_to_resolution = Optional(float, comment="The resolution time of the issue in days")
    days_of_down_time = Optional(float, comment="The time in days during which the issue was on pause while waiting for the client")
    affected_device_serial_number = Optional(str, comment="The composed serial number of the affected device (including manufacturer prefix)")
    client_id = Optional("Clients", csv_columns=[("Client Name", lambda l: l.full_name)], comment="The internal ID of the client affected by the issue", column="client_id")
    entry_by_user_id = Optional("Users", csv_columns=[("Entry User Name", lambda l: l.full_name)], reverse="issues_created", comment="The internal ID of the user that created the issue", column="entry_by_user_id")
    assigned_to_user_id = Optional("Users", csv_columns=[("Assigned User Name", lambda l: l.full_name)], reverse="issues_assigned", comment="The internal ID of the user assigned to the issue", column="assigned_to_user_id")

    # Virtual (not in table)
    if ENTERPRISE_FEATURES_ENABLED:
        interactions = Set("Interactions")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(issue):      
        return {
            "id": issue[0],
            "type": issue[1],
            "priority": IssuePriority.to_human(issue[2]),
            "status": IssueStatus.to_human(issue[3]),
            "start_date": issue[4],
            "end_date": issue[5],
            "days_to_resolution": issue[11].resolution_time(),
            "days_of_down_time": (issue[6].seconds//60) % 60 if issue[6] else None,
            "affected_device_serial_number": issue[7] or '',
            "client_id": issue[8].id if issue[8] else None,
            "entry_by_user_id": issue[9],
            "assigned_to_user_id": issue[10].id if issue[10] else None,
            "last_updated": issue[12]
        }

    @staticmethod
    def selector(objects):
        return select((
            i.id,
            i.type.name,
            i.priority,
            i.status,
            i.startDate,
            i.closedDate,
            i.downTime,
            i.device_serial_number,
            i.affectedClient,
            i.creator.id,
            i.assignee,
            i,
            Issues.extended_modified_date(i)
        ) for i in objects).order_by(13)
