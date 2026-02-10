from datetime import datetime
from decimal import Decimal
from pony.orm import Required, Optional, composite_key
from core_system.core_entities import db
from shared.helpers.db_helpers import TypeClassBase
from shared.helpers import date_helper
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid


class TokenType(TypeClassBase):
    add_credit = 'ADD_CREDIT'
    set_credit = 'SET_CREDIT'
    disable_payg = 'DISABLE_PAYG'
    pair_device = 'PAIR_DEVICE'

    TYPE_NAMES = {
        add_credit: 'Add Credit',
        set_credit: 'Set Credit',
        disable_payg: 'Disable PAYG',
        pair_device: 'Pair Device'
    }


class OfflineToken(db.Entity):
    uuid = Required(str)
    token = Required(str)
    generation_time = Required(datetime, default=datetime.now)
    commit_time = Optional(datetime)
    marked = Required(bool, default=False)
    used = Required(bool, default=False)
    deleted = Required(bool, default=False)
    type = Required(str, py_check=TokenType.valid)
    credit_value = Optional(Decimal)
    unit = Optional(str)
    device = Required('Device', column="device")
    modified_date = Required(datetime, default=date_helper.getDefaultDateStr, index=True)
    mobile_uuid = Optional(str, unique=True)

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    def before_update(self):
        self.modified_date = date_helper.getCurrentUtcDate()
    
    @property
    def modifiedDate(self):
        return self.modified_date


class OfflineTokenConfig(db.Entity):
    offer = Optional('Offer', column="offer")
    device_type = Optional(str)
    order = Required(int)
    type = Required(str, py_check=TokenType.valid)
    credit_value = Optional(Decimal)
    unit = Optional(str)

    composite_key(order, offer)
    composite_key(order, device_type)

    def get_type_name(self):
        return TokenType.TYPE_NAMES.get(self.type)

    def get_default_price(self):
        if not self.offer or not self.credit_value:
            return None
        minimum = self.offer.minimum_payment if self.offer.minimum_payment is not None else self.offer.base_price_amount
        bundles = [(self.offer.discount_price_2_amount, self.offer.discount_price_2_credit or float('inf')),
                   (self.offer.discount_price_1_amount, self.offer.discount_price_1_credit or float('inf')),
                   (minimum, self.offer.base_price_credit*minimum/self.offer.base_price_amount),
                   (0, -1)]
        for bundle in bundles:
            if bundle[1] <= self.credit_value:
                return self.credit_value*(bundle[0]/bundle[1])
