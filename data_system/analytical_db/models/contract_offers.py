from pony.orm import Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from payg_loan_system.offers.models import Offer, OfferType
from datetime import datetime
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from decimal import Decimal
import config


class Contract_Offers(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Contract Offers are the definition of the base terms of the contracts. All the contracts with one offer will have the same terms, except if they have some add-ons modifying some of those terms. '

    base_model = Offer

    id = PrimaryKey(int, comment="The internal unique ID of the contract offer")
    name = Optional(str, comment="The name of the contract offer")
    code = Optional(str, comment="The code of the contract offer, usually a shorthand for the name for easier idenfitication")
    type = Optional(str, comment="The type of the contract offer, either loan, paid upfront or a subscription")
    family = Optional(str, comment="The family of the contract offer, either targeted at homes or businesses")

    available_for_leads = Optional(bool, comment="True if the contract offer is available for new leads (in general, it might not be available in all entities)")
    can_be_registered = Optional(bool, comment="True if leads with this contract offer can be registered (in general, it might not be available in all entities)")
    approval_required = Optional(bool, comment="True if leads with this contract offer require approval")
    automatically_disable_payg = Optional(bool, comment="True if the attached PAYGO device (if any) should be unlocked forever at the end of a contract with that offer")

    credit_unit = Optional(str, comment="The credit unit of the contract offer. It is usually days, but it can also be month (for time-based subscription) or other units, such as kWh or liters (for usage-based subscriptions)")
    total_value = Optional(Decimal, comment="The total nominal value of a contract with that offer (excluding any changes made by add-ons)")
    deposit_amount = Optional(Decimal, comment="The amount of the deposit for a contract with that offer (if applicable)")
    credit_at_start = Optional(Decimal, comment="The number of credits given at the start of a contract with that offer (if applicable), before the first contract payment is to be made")
    loan_duration_days = Optional(Decimal, comment="The duration of the loan in days (only applicable to loan offers)")
    reference_payment_frequency_days = Optional(Decimal, comment="The expected number of days between each contract payments (if applicable). It is the same as the reference pricing credit but converted to days (assuming 30.437 days in a month for monthly offers)")

    minimum_payment = Optional(Decimal, comment="The minimum payment accepted for a contract with that offer (to trigger a contract payment)")
    reference_pricing_amount = Optional(Decimal, comment="The amount that is expected to be paid for one contract payment, it is higher than the minimum payment. ")
    reference_pricing_credit = Optional(Decimal, comment="The number of credits that are given for one contract payment of the reference pricing amount. For loans or time-based subscription this is the expected payment frequency (e.g. if the reference pricing credit is 7 and the amount is 1000 it means the client is expected to pay 1000 every 7 days)")
    discount_pricing_1_amount = Optional(Decimal, comment="The first discount pricing applies if the client pays above that amount")
    discount_pricing_1_credit = Optional(Decimal, comment="The number of credits that are given for one contract payment of the first discount pricing amount. The price per credit is lower than the reference pricing")
    discount_pricing_2_amount = Optional(Decimal, comment="The second discount pricing applies if the client pays above that amount")
    discount_pricing_2_credit = Optional(Decimal, comment="The number of credits that are given for one contract payment of the second discount pricing amount. The price per credit is lower than the first discount pricing")

    notes = Optional(str, comment="A free-form note about the contract offer")

    # Virtual (not in table)
    contracts = Set("Contracts")
    leads = Set("Leads")
    historical_stats = Set("Contracts_History")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(offer):
        loan = lambda x: x if x and offer.type == OfferType.loan else None
        time = lambda x: x if x and offer.type in [OfferType.loan, OfferType.time_based] else None
        completable = lambda x: x if x and offer.can_be_completed else None
        not_lump = lambda x: x if x and offer.type != OfferType.lump_sum else None
        return {
            "id": offer.id,
            "name": offer.name,
            "code": offer.code,
            "type": offer.get_human_readable_type_short_new(),
            "family": offer.family,
            "available_for_leads": offer.in_use,
            "can_be_registered": offer.in_use_for_new_clients,
            "approval_required": not offer.no_approval_required,
            "automatically_disable_payg": loan(offer.automatic_unlock_code_sending),
            "total_value": completable(offer.get_total_value_with_deposit()),
            "deposit_amount": time(offer.registration_fee),
            "loan_duration_days": loan(offer.get_days_to_ownership()),
            "credit_at_start": not_lump(offer.free_credit_at_start),
            "reference_pricing_credit": not_lump(offer.base_price_credit),
            "reference_pricing_amount": not_lump(offer.base_price_amount),
            "reference_payment_frequency_days": offer.reference_payment_frequency_days(),
            "minimum_payment": time(offer.minimum_payment),
            "discount_pricing_1_credit": not_lump(offer.discount_price_1_credit),
            "discount_pricing_1_amount": not_lump(offer.discount_price_1_amount),
            "discount_pricing_2_credit": not_lump(offer.discount_price_2_credit),
            "discount_pricing_2_amount": not_lump(offer.discount_price_2_amount),
            "notes": offer.notes or '',
            "credit_unit": offer.get_credit_unit(),
            "last_updated": Contract_Offers.extended_modified_date(offer)
        }

