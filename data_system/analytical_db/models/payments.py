from datetime import datetime
from pony.orm import select, Json, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWalletType
import config
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from decimal import Decimal


class Payments(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'This represent payments received by the system, they are not necessarily linked to anything and can be orphaned. They are used to track the source of every amount of money that is received by the company. '

    base_model = Payment

    id = PrimaryKey(int, comment="The internal unique ID of the payment")
    transaction_id = Optional(str, comment="The unique transaction ID of the payment. This is a series of character usually given by the payment provider (mobile money operator, credit card company, etc.)")
    date = Optional(datetime, comment="The date at which the payment was received on the system")
    amount = Optional(Decimal, comment="The amount of the payment")
    memo = Optional(str, comment="A text usually input by the person paying and used to reconcile the payment with its destination (contract, user, etc.)")
    source_type = Optional(str, comment="The type of the source of the payment (mobile money, cash collection, etc.)")
    payment_wallet_name = Optional(str, comment="The name of the wallet where the payment was received from. This is usually a unique identifier of the account (mobile money or bank) of the person paying")
    payment_wallet_id = Optional("Payment_Wallets", comment="The internal ID of the wallet where the payment was recieved")
    wallet_operator = Optional(str, comment="The code of the operator of the wallet (e.g. mobile money provider, bank service provider, etc.)")
    back_payment_id = Optional(int, comment="The internal ID of the back payment linked to this payment", column="back_payment_id")
    destinations = Optional(Json, comment="A JSON field that contains the destinations of the payment (contracts, users, etc.). This is useful to track destinations when payments are split between several destinations")

    # Virtual (not in table)
    reconciled_payments_id = Set("Reconciled_Payments")
    reversals = Set("Reversed_Payments", reverse="payment_id")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def bulk_allowed():
        return False # We cannot handle the destinations json field easily

    @staticmethod
    def converter(payment):
        return {
            "id": payment[0],
            "transaction_id": payment[1],
            "date": payment[2],
            "amount": float(payment[3]),
            "memo": payment[4] if payment[4] else "",
            "source_type": config.WALLET_HUMAN_READABLE_TYPES.get(payment[5], config.WALLET_HUMAN_READABLE_TYPES[None]),
            "payment_wallet_name": payment[6],
            "payment_wallet_id":payment[9].PaymentWallet.id,
            "wallet_operator": payment[7] or '',
            "back_payment_id": payment[8].id if payment[8] else None,
            "destinations": payment[9].get_destination_indicator(),
            "last_updated": payment[10]
        }

    @staticmethod
    def selector(objects):
        return select((
            p.id,
            p.Reference,
            p.PaymentTime,
            p.Amount,
            p.memo,
            p.PaymentWallet.Type,
            p.PaymentWallet.FullName,
            p.wallet_operator,
            p.back_payment,
            p,
            Payments.extended_modified_date(p)
        ) for p in objects).order_by(11)

    @staticmethod
    def filter(objects):
        return objects.filter(
            lambda p: p.PaymentWallet.Type in [PaymentWalletType.cash, PaymentWalletType.mobile_money]
        )
