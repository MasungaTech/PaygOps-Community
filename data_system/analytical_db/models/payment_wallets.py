from datetime import datetime
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.payments.models.wallet import PaymentWalletType
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from payg_loan_system.payments.models.wallet import PaymentWallet
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from decimal import Decimal
import config


class Payment_Wallets(analytical_db.Entity, BaseAnalyticalDBModel):
    _description_ = 'Payment wallets are information related to which provider the payment was made through, can be bank, mobile money service proovider or cash'

    base_model = PaymentWallet

    id = PrimaryKey(int, comment="The internal unique ID of the payment wallet")
    name = Optional(str, comment="The name of the payment wallet")
    phone_number = Optional(str, comment="The phone number tied to the payment wallet")
    wallet_operator = Optional(str, comment="The name name of the wallet operator")
    type = Optional(str, comment="The type of the wallet (e.g cash, mpesa or mentor-cash)")
    balance = Optional(Decimal, comment="The current balance amount in the payment wallet")
    total_payments = Optional(Decimal, comment="The total sum amount of all the payments made using the payment wallet")
    total_reconciliation_and_adjustments = Optional(Decimal, comment="The total sum amount of all reconciled payments made in the payment wallet")
    owner_name = Optional(str, comment="The full name of the owner of the payment wallet")
    first_payment_date = Optional(datetime, comment="The date the payment wallet was created")

    # Virtual not in database table
    payments = Set("Payments")
    reconciled_payments = Set("Reconciled_Payments")
    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(payment_wallet):
        if payment_wallet.client is not None:
            owner_name = payment_wallet.client
        elif payment_wallet.user is not None:
            owner_name = payment_wallet.user
        else:
            owner_name = payment_wallet.lead

        

        return {
            "id": payment_wallet.id,
            "name":payment_wallet.FullName,
            "phone_number":payment_wallet.phone_number.number if payment_wallet.phone_number is not None else '',
            "wallet_operator":payment_wallet.operator,
            "type":payment_wallet.type_name,
            "total_payments":payment_wallet.get_total_payments(),
            "total_reconciliation_and_adjustments":payment_wallet.get_total_reconciled(),
            "balance":payment_wallet.get_balance(),
            "owner_name": owner_name.full_name if owner_name else '',
            "first_payment_date":payment_wallet.RegistrationDate,
            "last_updated":Payment_Wallets.extended_modified_date(payment_wallet)    
        }

    @staticmethod
    def selector(objects):
        return select(wallet for wallet in objects).order_by(lambda w: w.id)

    
