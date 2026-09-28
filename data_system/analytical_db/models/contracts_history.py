from pony.orm.core import PrimaryKey
from payg_loan_system.contracts.models.contract_model import Contract
from data_system.analytical_db.analytical_db import analytical_db
from datetime import datetime, timedelta
from pony.orm import select, desc
from shared.helpers.db_helpers import Optional, PrimaryKey
from decimal import Decimal
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config


class Contracts_History(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'This table contains the historical state of the contracts for each month of the contract existence'

    base_model = Contract

    id = PrimaryKey(str, comment="The internal unique ID of the contract history point (in format year-month-day-contractID)")

    date = Optional(datetime, comment="The date of the contract history point (and end date of the period for the metrics that are in a period). All metrics below are considered to be for that date.")
    from_date = Optional(datetime, comment="The start date fo the period for the metrics that are in a period")

    offer_id = Optional("Contract_Offers", csv_columns=[("Offer Name", lambda c: c.name)], comment="The internal ID of the offer of the contract", column="offer_id")
    client_id = Optional("Clients", csv_columns=[("Client Name", lambda c: c.full_name)], comment="The internal ID of the client that has the contract", column="client_id")
    contract_id = Optional('Contracts', column="contract_id")
    contract_reference = Optional(str)

    amount_paid_in_period = Optional(Decimal, comment="The sum of the total amount of all the payments made on the contract during the period (including both amount paid directly and amount of discounts)")
    expected_amount_paid_in_period = Optional(Decimal, comment="The expected total amount paid within the period if the client had paid exactly on time until now. This takes into account any grace period given or other adjustment from add-ons")
    amount_of_discounts_in_period = Optional(Decimal, comment="The sum of all the discounts on all the payments made on the contract during the period (including both automatic discounts and manual discounts and any discount on initial deposit)")
    amount_paid_without_discounts_in_period = Optional(Decimal, comment="The sum of the amount paid without discounts on all the payments made on the contract during the period")

    next_contract_payment_due_date = Optional(datetime, comment="The date at which the next contract payment is due")
    days_before_contract_payment_due = Optional(float, comment="The number of days before the next contract payment is due. If it is negative it means payment is overdue")
    par_status_group = Optional(str, comment="The Portfolio at Risk (PAR) group to which the contract belongs (e.g. PAR 7, PAR 30, on time, etc.)")

    cumulative_amount_paid = Optional(Decimal, comment="The sum of the total amount of all the payments made on the contract (including both amount paid directly and amount of discounts)")
    expected_cumulative_amount_paid = Optional(Decimal, comment="The expected total amount paid if the client had paid exactly on time until now. This takes into account any grace period given or other adjustment from add-ons")
    cumulative_amount_in_arrears = Optional(Decimal, comment="The cumulative amount of payments that should have been made but were not. It is the difference between the expected cumulative amount paid and the cumulative amount paid")
    cumulative_days_in_arrears = Optional(float, comment="The cumulative time late on contract payments (including any payment currently due), this takes into account only days late, not days in advance")
    cumulative_amount_of_discounts = Optional(Decimal, comment="The sum of all the discounts on all the payments made on the contract (including both automatic discounts and manual discounts and any discount on initial deposit)")
    cumulative_amount_paid_without_discounts = Optional(Decimal, comment="The sum of the amount paid without discounts on all the payments made on the contract")

    days_since_contract_start = Optional(float, comment="Also called seasoning or seniority, it is the number of days since the contract started (or the time between the beginning and the end of the contract if the contract has ended)")
    payment_progression = Optional(float, comment="The progression of the contract payment, it is the cumulative amount paid over the nominal contract value")
    expected_payment_progression = Optional(float, comment="The expect payment progression of the contract if the client had paid exactly on time until now. It is the expected cumulative amount paid over the nominal contract value")
    timeliness_ratio = Optional(float, comment="It is a measure on how on time the contract payments were. It is the (days since contract started - cumulative days in arrears) / days since contract started. Note that for completed or defaulted contracts, the time since installation is instead the time to completion or default (end time)")

    nominal_contract_value = Optional(Decimal, comment="The nominal value of the contract. This takes into account both the value of the offer and the value of the add-ons added to the contract")
    cumulative_paid_upfront_addons_value = Optional(Decimal, comment="The sum of the value of the paid upfront add-ons added to the contract")
    cumulative_loan_change_addons_value = Optional(Decimal, comment="The sum of the value of the loan change add-ons added to the contract")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(contract, from_date, to_date):
        repaid_in_period = contract.get_cumulative_amount_repaid(to_date, from_time=from_date) or Decimal(0)
        discounted_in_period = contract.get_amount_discounted(to_date, from_time=from_date) or Decimal(0)
        expected_repaid_in_period = contract.get_expected_amount_repaid(to_date, from_time=from_date, cached=True) or Decimal(0)

        last_stat = Contracts_History.get_last_computed_stat(from_date, contract.id)
        if last_stat:
            cumulative_amount_paid = Decimal(last_stat.cumulative_amount_paid or 0) + repaid_in_period
            cumulative_amount_of_discounts = Decimal(last_stat.cumulative_amount_of_discounts or 0) + discounted_in_period
            expected_cumulative_amount_paid = Decimal(last_stat.expected_cumulative_amount_paid or 0) + expected_repaid_in_period
        else:
            cumulative_amount_paid = contract.get_cumulative_amount_repaid(to_date) or Decimal(0)
            cumulative_amount_of_discounts = contract.get_amount_discounted(to_date) or Decimal(0)
            expected_cumulative_amount_paid = contract.get_expected_amount_repaid(to_date, cached=True) or Decimal(0)

        total_value = contract.get_total_value(to_date)
        cumulative_days_in_arrears = contract.get_cumulative_days_in_arrears(to_date, use_cache=True)
        next_due_time = contract.get_repayment_due_time(to_date)

        return Contracts_History._convert_decimal_to_float_dict({
            'id': f'{to_date:%Y-%m-%d}-{contract.id}',

            'date': to_date,
            'from_date': from_date,

            'offer_id': contract.offer_at(to_date).id,
            'client_id': contract.client.id,
            'contract_id': contract.id,
            'contract_reference': contract.reference,

            'amount_paid_in_period': repaid_in_period,
            'expected_amount_paid_in_period': expected_repaid_in_period,
            'amount_of_discounts_in_period': discounted_in_period,
            'amount_paid_without_discounts_in_period': repaid_in_period-discounted_in_period,
            
            'next_contract_payment_due_date': next_due_time,
            'days_before_contract_payment_due': contract.get_days_until_next_payment(to_date, next_due_time=next_due_time),
            'par_status_group': contract.get_par_status_group(to_date, next_due_time=next_due_time),

            'cumulative_amount_paid': cumulative_amount_paid,
            'expected_cumulative_amount_paid': expected_cumulative_amount_paid,
            'cumulative_amount_in_arrears': contract.get_cumulative_amount_in_arrears(to_date, expected=expected_cumulative_amount_paid, repaid=cumulative_amount_paid, include_negative=True, cached=True),
            'cumulative_days_in_arrears': cumulative_days_in_arrears,
            'cumulative_amount_of_discounts': cumulative_amount_of_discounts,
            'cumulative_amount_paid_without_discounts': cumulative_amount_paid-cumulative_amount_of_discounts,

            'days_since_contract_start': contract.get_days_since_contract_start(to_date),
            'payment_progression': cumulative_amount_paid / total_value if total_value else 1,
            'expected_payment_progression': expected_cumulative_amount_paid / total_value if total_value else 1,
            'timeliness_ratio': contract.get_timeliness_ratio(to_date, cumulative_days_in_arrears=cumulative_days_in_arrears, use_cache=True),

            'nominal_contract_value': total_value,
            'cumulative_paid_upfront_addons_value': contract.get_total_value_of_lumpsum_addons(to_date),
            'cumulative_loan_change_addons_value': contract.get_total_extended(to_date),
            
            'last_updated': to_date 
        })

    @staticmethod
    def default_page_size_cat():
        return 3

    @staticmethod
    def selector(objects):
         return select(c for c in objects).order_by(Contract.id)

    @staticmethod
    def get_ids_for_dates(from_date, to_date):
        return select(contract.id for contract in Contract
                        if contract.start_time < to_date and
                        (not contract.end_time or contract.end_time >= from_date)).order_by(1)

    @classmethod
    def analytical_db_selector(cls, from_date, to_date):
        return select(csh for csh in cls if csh.from_date == from_date and csh.date == to_date)

    @staticmethod
    def get_oldest_date():
        return select(contract.start_time for contract in Contract).min()

    @staticmethod
    def get_last_computed_stat(from_date_current, contract_id):
        new_date = from_date_current - timedelta(seconds=1)
        return select(stat for stat in Contracts_History if 
                      stat.date >= new_date and stat.date <= from_date_current
                      and stat.contract_id.id == contract_id).order_by(lambda stat: desc(stat.date)).first()