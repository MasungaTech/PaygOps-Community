from datetime import datetime
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.payments.models.wallet import PaymentWalletType
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from payg_loan_system.contracts.models.reconciled_payment_model import ReconciledPayment
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from decimal import Decimal
import config


HUMAN_DESTINATION_NAMES = {
    'contract_repayment': 'Contract Payment',
    'lead': 'Lead',
    'add_on': 'Add-On',
    'user': 'User',
    'adjustment': 'Adjustment',
}


class Reconciled_Payments(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Reconciled payments are amount taken from a source and put to a use in a destination. They are linked both to a payment wallet and to a specific use (e.g. contract payment, user, etc.). In most cases they are linked one to one with a payment, but occasionally it can be more complex (i.e. two payments of 500 on two separate wallets paying for one contract payment of 1000, or one big payment of 2000 paying for two 1000 contract payments on two different contracts). '

    base_model = ReconciledPayment

    id = PrimaryKey(int, comment="The internal unique ID of the reconciled payment")
    date = Optional(datetime, comment="The date at which the reconciliation was made")
    amount = Optional(Decimal, comment="The amount of the reconciliation")
    type = Optional(str, comment="The type of the reconciliation (e.g. contract payment, payment reversal, user, etc.)")
    note = Optional(str, comment="A free-form note about the reconciliation providing extra details (either from the system or from a user directly)")
    payment_wallet_name = Optional(str, comment="The name of the payment wallet on which the reconciliation was done. This is usually a unique identifier of the account (mobile money or bank) of the person paying")

    destination_type = Optional(str, comment="The type of the destination of the reconciliation (e.g. contract, user, etc.)")
    destination_contract_reference = Optional(str, comment="The reference of the destination contract or lead (if any)")
    
    origin_payment_id = Optional("Payments", comment="The internal ID of the payment on which the reconciliation was done", column='origin_payment_id')
    origin_payment_transaction_id = Optional(str, comment="The transaction ID of the payment on which the reconciliation was done")
    payment_wallet_id = Optional("Payment_Wallets", comment="The internal ID of the payment wallet on which the reconciliation was done")
    origin_reconciled_payment_id = Optional("Reconciled_Payments", comment="The internal ID of the origin reconciled payment on which the reconciliation was done if it was reconciled from one contract (overpaid) to another", column='origin_reconciled_payment_id')


    lead_id = Optional("Leads", comment="The internal ID of the destination lead on which the reconciliation was done (if any)", column='lead_id')
    add_on_id = Optional("AddOns", comment="The internal ID of the destination add-on on which the reconciliation was done (if any)", column='add_on_id')
    contract_payment_id = Optional("Contract_Payments", comment="The internal ID of the destination contract payment on which the reconciliation was done (if any)", column='contract_payment_id')
    contract_pending_payment_id = Optional("Contracts", comment="The internal ID of the destination contract on which the reconciliation is pending to be done (if any)", column='contract_pending_payment_id')
    user_id = Optional("Users", comment="The internal ID of the destination user on which the reconciliation was done (if any)", column='user_id')
    client_id = Optional('Clients', comment="The internal ID of the client with the pending reconciliation", column="client_id")
    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    destination_reconciled_payments = Set('Reconciled_Payments')

    @staticmethod
    def converter(reconciled_payment):
        destination_indicator = reconciled_payment[11].get_destination_indicator()
        return {
            "id": reconciled_payment[0],
            "date": reconciled_payment[1],
            "amount": float(-reconciled_payment[2]),
            "type": ReconciledPaymentType.to_human(reconciled_payment[3]) or '',
            "note": reconciled_payment[4] or '',
            "payment_wallet_name": reconciled_payment[5],
            "destination_type": HUMAN_DESTINATION_NAMES.get(destination_indicator['destination_type'], destination_indicator['destination_type']),
            "destination_contract_reference": destination_indicator.get('destination', ''),
            "contract_payment_id": reconciled_payment[6].id if reconciled_payment[6] else None,
            "add_on_id": reconciled_payment[7].id if reconciled_payment[7] else None,
            "lead_id": reconciled_payment[8].id if reconciled_payment[8] else None,
            "user_id": reconciled_payment[12].id if reconciled_payment[12] else None,
            "origin_payment_id": reconciled_payment[9].id if reconciled_payment[9] else None,
            "origin_payment_transaction_id": reconciled_payment[9].Reference if reconciled_payment[9] else '',
            "origin_reconciled_payment_id": reconciled_payment[15].id if reconciled_payment[15] else None,
            "payment_wallet_id": reconciled_payment[11].payment_account.id,
            "contract_pending_payment_id": reconciled_payment[10].id if reconciled_payment[10] else None,
            "last_updated": reconciled_payment[13],
            "client_id": reconciled_payment[14].client.id if reconciled_payment[14] else None,
        }

    @staticmethod
    def selector(objects):
        return select((
            p.id,
            p.time,
            p.amount,
            p.type,
            p.note,
            p.payment_account.FullName,
            p.repayment,
            p.add_on,
            p.lead,
            p.linked_payment,
            p.contract_pending_repayment,
            p,
            p.user,
            Reconciled_Payments.extended_modified_date(p),
            p.person,
            p.origin_reconciled_payment
        ) for p in objects).order_by(13)

    @staticmethod
    def filter(objects):
        return objects.filter(
            lambda p: p.payment_account.Type in [PaymentWalletType.cash, PaymentWalletType.mobile_money]
        )
