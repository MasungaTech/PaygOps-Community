import factory
from functools import partial
from payg_loan_system.offers.models import LoanOffer, Offer, OfferType
from payg_loan_system.offers.interfaces import OfferInterfaces
from decimal import Decimal


class TimeOfferFactory(factory.Factory, OfferInterfaces):
    class Meta:
        model = Offer

    id = factory.Sequence(lambda n: n)
    type = OfferType.loan
    name = 'PATCH OFFER'
    code = '20H'+str(id)
    family = 'Home'
    in_use = True
    in_use_for_new_clients = False
    registration_fee = Decimal(10000)
    time_to_ownership_in_days = Decimal(52 * 7)
    free_credit_at_start = Decimal(7)
    no_approval_required = True
    device_type = ''
    unit_cost = Decimal(100000)
    lighting_global_compliant = True
    minimum_payment = None
    base_price_amount = Decimal(9500)
    base_price_credit = Decimal(7)
    discount_price_1_amount = Decimal(9500*4)
    discount_price_1_credit = Decimal(4*7+4)
    discount_price_2_amount = Decimal(9500*6)
    discount_price_2_credit = Decimal(6*7+7)
    panel_size_in_w = 10
    battery_size_in_ah = 5
    credit_unit = None
    payment_frequency = None
    allow_pro_rata = True
    payment_day_of_month = None
    forgive_lateness = True
    is_monthly = False
    can_be_completed = True

    @classmethod
    def stub(cls, *args, **kwargs):
        offer = super().stub(*args, **kwargs)
        offer.linked_to_product = True
        offer.get_required_device_type = partial(LoanOffer.get_required_device_type, offer)
        offer.get_total_value_with_deposit = partial(LoanOffer.get_total_value_with_deposit, offer)
        offer.get_time_to_pay = partial(LoanOffer.get_time_to_pay, offer)
        offer.get_ratio_of_price_with_other_offer = partial(LoanOffer.get_ratio_of_price_with_other_offer, offer)
        offer.get_total_value_without_deposit = partial(LoanOffer.get_total_value_without_deposit, offer)
        offer.get_fully_discounted_loan_amount_with_deposit = partial(LoanOffer.get_fully_discounted_loan_amount_with_deposit, offer)
        offer.get_most_discounted_price = partial(LoanOffer.get_most_discounted_price, offer)
        offer.get_base_price_per_credit = partial(LoanOffer.get_base_price_per_credit, offer)
        offer.get_discount_1_price_per_credit = partial(LoanOffer.get_discount_1_price_per_credit, offer)
        offer.get_discount_2_price_per_credit = partial(LoanOffer.get_discount_2_price_per_credit, offer)
        offer.get_human_readable_type = partial(LoanOffer.get_human_readable_type, offer)
        offer.discount_applies = partial(LoanOffer.discount_applies, offer)
        offer.apply_discount = partial(LoanOffer.apply_discount, offer)
        offer.get_discount_amount = partial(LoanOffer.get_discount_amount, offer)
        offer.get_discount_rate = partial(LoanOffer.get_discount_rate, offer)
        offer.add_credit = partial(LoanOffer.add_credit, offer)
        return offer


class TimeOfferAbstractFactory:
    @staticmethod
    def create():
        return TimeOfferFactory.stub()
