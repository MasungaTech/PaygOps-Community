from data_system.analytical_db.analytical_db import analytical_db
from payg_loan_system.contracts.models.repayment_model import ContractRepayment, ContractRepaymentDiscountTypes
from datetime import datetime
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from shared.helpers.numbers import float_if_exists
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from decimal import Decimal
import config


class Contract_Payments(analytical_db.Entity, BaseAnalyticalDBModel):

    base_model = ContractRepayment

    _description_ = 'Contract Payments (formerly "Repayments") are payments made to a Contract, by opposition to payments that can be linked to either contract or other things or orphaned. One contract payment can be made with several payments and one payment can be used to make several contract payments. '

    id = PrimaryKey(int, comment="The internal unique ID of the contract payment")
    contract_id = Optional("Contracts", comment="The internal ID of the contract this contracty payment is related to", column="contract_id")
    contract_reference = Optional(str, comment="The reference of the contract this contract payment is related to")
    client_id = Optional("Clients", comment="The internal ID of the client this contract payment is related to", column="client_id")
    payment_date = Optional(datetime, comment="The date at which the payment was actually made (reconciled) on the contract")
    expected_payment_date = Optional(datetime, comment="The date at which the payment was expected to be made on the contract")
    days_late = Optional(float, comment="The number of days between the payment date and the expected payment date")
    total_amount = Optional(Decimal, comment="The total amount paid, including any discounts")
    amount_paid = Optional(Decimal, comment="The amount paid, excluding any discounts")
    amount_of_discount = Optional(Decimal, comment="The amount of discounts given (if any)")
    credit_value = Optional(Decimal, comment="The number of credits given as a result of that contract payment")
    type = Optional(str, comment="The type of the contract payment (e.g. Downpayment, Reversed Payment, etc.)")

    # Virtual (not in table)
    reconciled_payments = Set('Reconciled_Payments')
    contract_events = Set('Contract_Events')

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(repayment):
        return {
            "id": repayment[0],
            "contract_id": repayment[1],
            "contract_reference": repayment[2],
            "client_id":repayment[3],
            "payment_date": repayment[5],
            "expected_payment_date": repayment[6],
            "total_amount": repayment[4],
            "amount_paid": repayment[7],
            "amount_of_discount": repayment[8],
            "days_late": float_if_exists(repayment[9]/24) if repayment[9] else None,
            "credit_value": repayment[11],
            "type": ContractRepaymentDiscountTypes.to_human(repayment[13]) or '',
            "last_updated": repayment[14]
        }

    @staticmethod
    def selector(objects):
        return select((
            p.id,
            p.contract.id,
            p.contract.reference,
            p.contract.client.id,
            p.amount,
            p.time,
            p.expected_time,
            p.amount_paid,
            p.amount_discounted,
            p.hours_late,
            p.amount_late,
            p.credit_value,
            p.credit_unit,
            p.discount_type,
            Contract_Payments.extended_modified_date(p)
        ) for p in objects).order_by(15)
