from datetime import datetime

from pony.orm import select

import config
from data_system.analytical_db.analytical_db import analytical_db
from data_system.analytical_db.models.base_analytical_db_model import \
    BaseAnalyticalDBModel
from payg_loan_system.reversed_payments.models import ReversedPayment
from shared.helpers.db_helpers import Optional, PrimaryKey


class Reversed_Payments(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'This represents payment reversal requests received by the system. This does not mean the payment was actually reversed, this is reflected in the status of the reversed payment. '

    base_model = ReversedPayment

    id = PrimaryKey(int, comment="The internal unique ID of the payment reversal")
    reversal_id = Optional(str, comment="The unique ID (external) of the payment reversal. This is a series of character usually given by the payment provider (mobile money operator, credit card company, etc.)")
    reversal_date = Optional(datetime, comment="The date at which the payment was reversed on the system")

    status = Optional(str, comment="The status of the payment reversal. Can be either handled or unhandled")
    approver_id = Optional("Users", comment="The internal ID of the user that approved the reversal")
    payment_id = Optional("Payments", csv_columns=[("Payment Transaction ID", lambda p: p.transaction_id), ("Payment Date", lambda p: p.date), ("Payment Amount", lambda p: p.amount), ("Payment Memo", lambda p: p.memo), ("Payment Destinations", lambda p: p.destinations)], comment="The internal ID of the payment that was reversed")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def bulk_allowed():
        return True

    @staticmethod
    def converter(reversal):
        return {
            "id": reversal[0],
            "reversal_id": reversal[1],
            "reversal_date": reversal[2],
            "status": 'handled' if reversal[3] else 'unhandled',
            "approver_id": reversal[4].id if reversal[4] else None,
            "payment_id": reversal[5].id if reversal[5] else None,
            "last_updated": reversal[6]
        }

    @staticmethod
    def selector(objects):
        return select((
            r.id,
            r.reference_code,
            r.reversed_on,
            r.handled,
            r.user,
            r.payment,
            Reversed_Payments.extended_modified_date(r)
        ) for r in objects).order_by(7)
