from datetime import datetime
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from payg_loan_system.contracts.models.contract_model import Contract
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config
from decimal import Decimal


class Contracts(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Contracts define the terms and current status of a purchase from a client, it can be either a Loan, Paid Upfront or a Subscription (time-based or usage-based).'

    base_model = Contract

    id = PrimaryKey(int, comment="The internal unique ID of the contract")
    reference = Optional(str, comment="The unique reference of the contract")

    status = Optional(str, comment="The current status of the contract (e.g. active, defaulted, completed, paused)")
    start_date = Optional(datetime, comment="The date at which the contract started (when the registration happened)")
    end_date = Optional(datetime, comment="The effective end date of the contract (when it was either completed or defaulted)")
    repossession_date = Optional(datetime, comment="Also called foreclosure date, it is the date at which the assets were repossessed (in case of default)")
    
    offer_id = Optional("Contract_Offers", csv_columns=[("Offer Name", lambda c: c.name), ("Offer Type", lambda c: c.type)], comment="The internal ID of the offer of the contract", column="offer_id")
    client_id = Optional("Clients", csv_columns=[("Client Name", lambda c: c.full_name)], comment="The internal ID of the client that has the contract", column="client_id")
    lead_id = Optional("Leads", column="lead_id", comment="The ID of the lead linked to the contract")
    lead_generator_id = Optional("Lead_Generators", csv_columns=[("Lead Generator Name", lambda l: l.full_name)], comment="The internal ID of the lead generator that brought the contract", column="lead_generator_id")
    portfolio_id = Optional("Portfolios", csv_columns=[("Portfolio Name", lambda c: c.name)], comment="The internal ID of the portfolio of the contract (if any)", column="portfolio_id")

    device_serial_number = Optional(str, comment="The composed serial number of the device linked to the contract (if any)")

    next_contract_payment_due_date = Optional(datetime, comment="The date at which the next contract payment is due")
    days_before_contract_payment_due = Optional(float, comment="The number of days before the next contract payment is due. If it is negative it means payment is overdue and it represents the number of days late. ")
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

    nominal_contract_value = Optional(Decimal, comment="The nominal value of the contract (Yearly nominal value for Time Based Subscriptions). This takes into account both the value of the offer and the value of the add-ons added to the contract")
    deposit_amount = Optional(Decimal, comment="The amount of the deposit paid for the contract")
    reference_pricing_amount = Optional(Decimal, comment="The amount that is expected to be paid for one contract payment, taking into account any loan change add-on")
    reference_pricing_credit = Optional(Decimal, comment="The number of credits that are given for one contract payment of the reference pricing amount, taking into account any loan change add-on. For loans or time-based subscription this is the same as the expected payment frequency")
    reference_payment_frequency_days = Optional(Decimal, comment="The expected number of days between each contract payments of the reference pricing amount (if applicable). It is the same as the reference pricing credit but converted to days (assuming 30.437 days in a month for monthly offers)")
    total_duration_days = Optional(Decimal, comment="The total expected duration of the contract in days (for loans)")
    cumulative_paid_upfront_addons_value = Optional(Decimal, comment="The sum of the value of the paid upfront add-ons added to the contract")
    cumulative_loan_change_addons_value = Optional(Decimal, comment="The sum of the value of the loan change add-ons added to the contract")
    
    cumulative_credits_bought = Optional(Decimal, comment="The sum of all the credits bought by the contract payment made (usually days, see the credit unit)")
    credit_unit = Optional(str, comment="The credit unit of the contract. It is usually days, but it can also be month (for time-based subscription) or other units, such as kWh or liters (for usage-based subscriptions)")
    

    # Virtual (not in table)
    pending_reconciled_payments = Set("Reconciled_Payments")
    repayments = Set("Contract_Payments")
    events = Set("Contract_Events")
    contract_stats_historical = Set('Contracts_History')
    add_ons = Set("AddOns")
    stock_items = Set("Stock_Items")
    quantity_stock_items = Set('Quantity_Stock_Items')
    if config.ENABLE_ENTERPRISE_FEATURES:
        tasks = Set('Tasks')
    
    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def default_page_size_cat():
        return 4

    @staticmethod
    def converter(contract):
        c = contract[11]
        offer = contract[13]
        return {
            "id": contract[0],
            "reference": contract[9],

            "status": contract[7],
            "start_date": contract[4],
            "end_date": contract[5],
            "repossession_date": contract[6],

            "offer_id": contract[2],
            "client_id": contract[1],
            "lead_id": contract[8],
            'lead_generator_id': contract[12].id if contract[12] else None,
            "portfolio_id": contract[10].id if contract[10] else None,

            "device_serial_number": contract[3].composed_serial if contract[3] else "",        
            
            'next_contract_payment_due_date': c.next_repayment_due_time,
            'days_before_contract_payment_due': c.get_days_until_next_payment(),
            'par_status_group': c.get_par_status_group(),

            'cumulative_amount_paid': c.get_cumulative_amount_repaid(cached=True),
            'expected_cumulative_amount_paid': c.get_expected_amount_repaid(cached=True),
            'cumulative_amount_in_arrears': c.get_cumulative_amount_in_arrears(cached=True, include_negative=True),
            'cumulative_days_in_arrears': c.get_cumulative_days_in_arrears(cached=True),
            'cumulative_amount_of_discounts': c.get_amount_discounted(cached=True),
            'cumulative_amount_paid_without_discounts': c.get_amount_paid_without_discount(cached=True),

            'days_since_contract_start': c.get_days_since_contract_start(),
            'payment_progression': c.get_percentage_repaid(cached=True),
            'expected_payment_progression': c.get_expected_percentage_repaid(cached=True),
            'timeliness_ratio': c.get_timeliness_ratio(cached=True),

            'nominal_contract_value': c.get_total_value(cached=True) or c.get_yearly_value(),
            'deposit_amount': c.get_total_downpayment(), # SLOOOW
            'reference_pricing_amount': c.reference_price_at(cached=True),
            'reference_pricing_credit': offer.base_price_credit,
            'reference_payment_frequency_days': offer.reference_payment_frequency_days(),
            'total_duration_days': c.get_total_days_to_ownership(cached=True),
            'cumulative_paid_upfront_addons_value': c.get_total_value_of_lumpsum_addons(cached=True),
            'cumulative_loan_change_addons_value': c.get_total_extended(cached=True),

            'cumulative_credits_bought': c.get_credits_bought(), # SLOOOW
            'credit_unit': offer.get_credit_unit(),
            "last_updated": datetime.now()
    
        }

    @staticmethod
    def selector(objects):
        return select((
            c.id,
            c.client.id,
            c.offer.id,
            c.linked_device,
            c.start_time,
            c.end_time,
            c.repossession_time,
            c.status,
            c.lead.id,
            c.reference,
            c.portfolio,
            c,
            c.lead.generator,
            c.offer
        ) for c in objects).order_by(1)
