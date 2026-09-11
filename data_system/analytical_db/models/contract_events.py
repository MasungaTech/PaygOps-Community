from calendar import c
from data_system.analytical_db.analytical_db import analytical_db
from payg_loan_system.contracts.models.contract_event_model import ContractEvent, ContractEventType
from datetime import datetime
from pony.orm import select
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


class Contract_Events(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Events related to contracts, such as creation, changes, etc.'

    base_model = ContractEvent

    id = PrimaryKey(int, comment="The internal unique ID of the contract event")
    contract_id = Optional("Contracts", comment="The internal ID of the contract this event is related to", column="contract_id")
    contract_reference = Optional(str, comment="The reference of the contract this event is related to")
    date = Optional(datetime, comment="The date of the event")
    type = Optional(str, py_check=ContractEventType.ovalid, comment="The type of the event")
    contract_payment_id = Optional("Contract_Payments", comment="The internal ID of the contract payment related to this event (if any)", column="contract_payment_id")
    approved_by_user_id = Optional("Users", csv_columns=[("Approver User Name", lambda l: l.full_name)], comment="The internal ID of the user who approved this event (if any)", column="approved_by_user_id")
    narration = Optional(str, comment="The details of the event, with any relevant information (e.g. serial number of old and new device for a swap, number of days of delay given, etc.)")
    note = Optional(str, comment="A free-form note about the event")

    # Internal
    last_updated = Optional(datetime, config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(contract_event):
        return {
            "id": contract_event[0],
            "contract_id": contract_event[7],
            "contract_reference": contract_event[1],
            "date": contract_event[2],
            "type": contract_event[3] or '',
            "contract_payment_id": contract_event[4].id if contract_event[4] else None,
            "approved_by_user_id": contract_event[5].id if contract_event[5] else None,
            "narration": contract_event[8].get_narration() or '',
            "note": contract_event[6] if contract_event[6] else "",
            "last_updated": contract_event[9]
        }

    @staticmethod
    def selector(objects):
        return select((
            c.id,
            c.contract.reference,
            c.time,
            c.type,
            c.repayment,
            c.approver,
            c.note,
            c.contract.id,
            c,
            Contract_Events.extended_modified_date(c)
        ) for c in objects).order_by(10)
