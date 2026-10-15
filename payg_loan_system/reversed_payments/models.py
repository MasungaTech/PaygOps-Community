from datetime import datetime
from decimal import Decimal
from pony.orm import Required, Optional, select, PrimaryKey
from core_system.core_entities import db
from shared.model.interface import ModelInterface
from shared.logger.loggers import Error


class ReversedPayment(ModelInterface, db.Entity):
    _table_ = 'reversed_payment'

    id = PrimaryKey(int, auto=True)
    reference_code = Required(str, unique=True)
    payment_code = Required(str)

    amount = Optional(Decimal)
    sender_msisdn = Optional(str)
    sender_name = Optional(str)
    wallet_operator = Optional(str, index=True)

    payment = Optional("Payment")
    reversed_on = Optional(datetime)
    received_on = Required(datetime, default=datetime.now)

    malicious = Optional(bool)

    handled = Optional(bool, default=False)

    deleted_on = Optional(datetime)
    modified_on = Optional(datetime)

    user = Optional("User", column='user')
    reconciled_payment = Optional("ReconciledPayment")

    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    def get_link(self):
        from flask import url_for
        return url_for('reversed_payment.view_reversal', reversal_id=self.id)

    def get_display_id(self):
        return str(self.id)

    def check_data_coherence(self):
        if self.amount and round(self.amount, 2) !=self.amount:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')

    def before_insert(self):
        self.check_data_coherence()

    def before_update(self):
        self.modified_on = datetime.now()
        self.check_data_coherence()
        
    @staticmethod
    def all_unhandled():
        return select(rp for rp in ReversedPayment
                      if rp.handled is False)

    @staticmethod
    def all_handled():
        return select(rp for rp in ReversedPayment
                      if rp.handled)

    def get_serialized_object(self, **kwargs):
        return {
            'reference': self.reference_code,
            'payment_reference': self.payment_code,
            'sent_datetime': self.reversed_on,
            'sender_msisdn': self.sender_msisdn,
            'sender_name': self.sender_name,
            'amount': self.amount,
            'wallet_operator': self.wallet_operator
        }
