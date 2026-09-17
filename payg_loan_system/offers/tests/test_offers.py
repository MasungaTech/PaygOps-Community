from decimal import Decimal
from payg_loan_system.contracts.services.tests.factories import ContractFactory
from pony import orm
from payg_loan_system.offers.models import LoanOffer, Offer, OfferType
from payg_loan_system.offers.tests.factories import TimeOfferFactory


class TestOffers:

    @orm.db_session
    def test_create_offer(self):
        LoanOffer(
            name='Test Offer',
            code='TO',
            family='Home',
            in_use=True,
            in_use_for_new_clients=True,
            registration_fee=100000,
            time_to_ownership_in_days=7*100,
            free_credit_at_start=7,
            no_approval_required=True,
            device_type='NPG',
            unit_cost=200000,
            lighting_global_compliant=False,
            base_price_amount=1000,
            base_price_credit=7,
            discount_price_1_amount=2000,
            discount_price_1_credit=15,
            panel_size_in_w=10,
            battery_size_in_ah=5,
        )

    def test_get_base_hourly_price(self):
        this_offer = TimeOfferFactory.stub(
            base_price_amount=10000,
            base_price_credit=1000
        )
        assert this_offer.get_base_price_per_credit() == Decimal(10)

    def test_get_most_discounted_price(self):
        this_offer = TimeOfferFactory.stub()
        assert this_offer.get_most_discounted_price() == this_offer.discount_price_2_amount / this_offer.discount_price_2_credit

    def test_get_time_from_amount_base_time(self):
        contract = ContractFactory.stub()
        amount_paid = contract.offer.base_price_amount
        assert int(round(contract.get_units_from_amount(amount_paid))) == contract.offer.base_price_credit

    def test_get_time_from_amount_discount_1(self):
        contract = ContractFactory.stub()
        amount_paid = contract.offer.discount_price_1_amount
        assert int(round(contract.get_units_from_amount(amount_paid))) == contract.offer.discount_price_1_credit

    def test_get_time_from_amount_discount_2(self):
        contract = ContractFactory.stub()
        amount_paid = contract.offer.discount_price_2_amount
        assert int(round(contract.get_units_from_amount(amount_paid))) == contract.offer.discount_price_2_credit

    def test_get_time_from_amount_other_amount_1(self):
        contract = ContractFactory.stub()
        amount_paid = 40000
        expected_time = int(round(Decimal(amount_paid) / (Decimal(38000)/(32))))
        assert int(round(contract.get_units_from_amount(amount_paid))) == expected_time

    def test_get_time_from_amount_other_amount_2(self):
        contract = ContractFactory.stub()
        amount_paid = 12000
        expected_time = int(round(Decimal(amount_paid) / (Decimal(9500)/(7))))
        assert int(round(contract.get_units_from_amount(amount_paid))) == expected_time

    def test_get_total_value_without_deposit(self):
        this_offer = TimeOfferFactory.stub()
        # We have 52 weeks to ownership, so 8736 hours
        # We have 168 hours free, so total time to pay is 8568 hours
        # The base hourly cost is 9500 per week (so 9500 per 168 hours)
        amount_to_repay_without_deposit = 8568 * (Decimal(9500)/168)
        assert this_offer.get_total_value_without_deposit() == amount_to_repay_without_deposit

    def test_get_total_value_with_deposit(self):
        this_offer = TimeOfferFactory.stub()
        expected_value = this_offer.get_total_value_without_deposit() + this_offer.registration_fee
        assert this_offer.get_total_value_with_deposit() == expected_value

    def test_get_fully_discounted_loan_amount_with_deposit(self):
        this_offer = TimeOfferFactory.stub()
        # We have 52 weeks to ownership, so 8736 hours
        # We have 168 hours free, so total time to pay is 8568 hours
        # The most discounted cost is (57000) per 6 weeks + 7 days or 1176 hours
        amount_to_repay_without_deposit = 8568 * (Decimal(57000) / 1176)
        expected_amount = amount_to_repay_without_deposit + this_offer.registration_fee
        assert this_offer.get_fully_discounted_loan_amount_with_deposit() == round(expected_amount, 2)

    def test_get_ratio_of_price_with_other_offer(self):
        this_offer = TimeOfferFactory.stub()
        new_offer_weekly_price = Decimal(14250) # 1.5 times more expensive, we dont care about deposit for that (2/3 ratio)
        new_offer = TimeOfferFactory.stub(
            base_price_amount=new_offer_weekly_price
        )
        assert this_offer.get_ratio_of_price_with_other_offer(new_offer) == Decimal(2)/Decimal(3)
