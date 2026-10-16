from datetime import datetime
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from sales_system.leads.models.status_change_history import StatusChangesHistory
from sales_system.leads.models.lead_status import LeadStatus
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


class Leads_History(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'This table contains the history of the leads with some key data points recorded every time the lead status changes'

    base_model = StatusChangesHistory

    id = PrimaryKey(int, comment="The internal unique ID of the lead change")
    lead_id = Optional('Leads', csv_columns=[("Lead Name", lambda l: l.full_name)], comment="The internal ID of the lead that was changed", column="lead_id")
    date = Optional(datetime, comment="The date of the lead change")
    status = Optional(str, comment="The new status of the lead after the change")
    status_category = Optional(str, comment="The new status category of the lead after the change")
    note = Optional(str, comment="The last free-form note on the lead")
    next_contact_date = Optional(datetime, comment="The date at which the next contact with the lead was plannified")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(lc):
        return {
            "id": lc.id,
            "lead_id": lc.lead.id,
            "date": lc.date,
            "status": lc.status,
            "status_category": lc.status_id.category if lc.status_id else '',
            "note": lc.status_comment,
            "next_contact_date": lc.next_contact,
            'last_updated': Leads_History.extended_modified_date(lc)
        }

