from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.actions.default import handle_default_request
from payg_loan_system.actions.give_discount import give_discount
from payg_loan_system.actions.give_delay import handle_give_delay_request
from payg_loan_system.actions.swap_device import handle_device_change_request
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from payg_loan_system.actions.collect_cash import handle_paycash_request
from core_system.users.models.user_model import User
from datetime import datetime, timedelta
from decimal import Decimal
from payg_loan_system.offers.models import OfferType
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from pony.orm import db_session, desc
from shared.helpers.client_creator import ClientCreator
from messages_system.models.sms_db import OutgoingSMS
from shared.helpers.assert_datetime import assert_datetime


class TestTimeBasedOffers():

    @db_session
    def test_time_based_journey(self, api_client, good_api_key):

        lead = ClientCreator.create_lead(offer_data={
            "name": "TEST_FLOW_TIME_BASED",
            "code": "TEST_FLOW_TIME_BASED",
            "type": "Time Based",
            "base_price_amount": 2,
            "base_price_time_in_days": 1,
            "time_given_at_start_in_days": 0,
            "family": "Home",
            "downpayment": 0
        })

        client = ClientCreator.register_lead(api_client, good_api_key, lead)

        assert 'Welcome to our client family!' in self._get_last_message()

        contract = lead.contract
        assert contract.get_hours_before_payment_due() < 2*3600 #less than 2 secs
        assert contract.get_total_extended() == 0
        assert contract.get_total_extended(cached=True) == 0
        assert contract.get_total_value() is None
        assert contract.get_total_value(cached=True) is None
        assert contract.get_yearly_value() == 365*2
        assert contract.get_total_days_to_ownership() is None
        assert contract.get_total_days_to_ownership(cached=True) is None
        assert contract.get_total_value_without_deposit() is None
        assert contract.get_outstanding_balance() is None
        assert contract.get_outstanding_balance_discounted() is None
        assert contract.get_expected_oustanding_balance() is None
        assert contract.get_cumulative_amount_repaid() == 0
        assert contract.get_cumulative_amount_repaid(cached=True) == 0
        assert contract.get_cumulative_amount_repaid_this_year() == 0
        assert contract.get_cumulative_amount_repaid_without_deposit() == 0
        assert contract.get_amount_discounted() == 0
        assert contract.get_amount_discounted(cached=True) == 0
        assert contract.get_amount_paid_without_discount() == 0
        assert contract.get_expected_amount_repaid() == 2
        assert contract.get_percentage_repaid() is None
        assert contract.get_percentage_repaid(cached=True) is None
        assert contract.get_expected_percentage_repaid() is None
        assert contract.get_timeliness_ratio() == 0
        assert contract.get_weeks_progression_dict() is None
        assert contract.get_total_value_of_lumpsum_addons() == 0
        assert contract.get_total_value_of_lumpsum_addons(cached=True) == 0
        assert contract.get_value_of_lumpsum_addons_discounts() == 0
        assert contract.get_value_of_lumpsum_addons_paid_without_discount() == 0
        assert_datetime(contract.get_date_last_current(), datetime.now(), seconds=7)
        assert_datetime(contract.get_date_last_in_arrears(), datetime.now())
        assert contract.get_number_of_non_null_repayments() == 0
        assert contract.get_cumulative_days_in_arrears() < 1e-4
        assert contract.get_net_cumulative_days_in_arrears() < 1e-4
        assert contract.get_days_in_arrears_since_last_payment() < 1e-4
        assert contract.get_amount_in_arrears_since_last_payment() == contract.get_expected_amount_repaid() \
            == contract.get_net_cumulative_amount_in_arrears() == contract.get_cumulative_amount_in_arrears()
        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert contract.get_date_of_maturity_without_lateness() is None
        assert contract.get_date_of_maturity() is None
        assert contract.get_default_amount() is None
        assert contract.get_gogla_default_date() is None


    @db_session
    def test_full_time_based_journey(self, api_client, good_api_key, super_admin_user):
        #create offer
        offer = CreateOfferService.add_from_data_and_user({
            "code": "TTB-123",
            "name": "Test Time Based Offer",
            "type": OfferType.time_based,
            "downpayment": 230000,
            "free_credit_at_start_time_based": 7,
            "base_price_amount": 1000,
            "base_price_time_in_days": 7,
            "family": 'Home',
            "in_use_for_new_leads": "True",
            "can_be_approved_and_registered": "True"
        }, super_admin_user())
        
        #create lead
        lead = ClientCreator.create_lead(offer_data={
            "name": offer.name,
            "code": offer.code,
            "type": offer.type,
            "credit_unit": offer.credit_unit,
            "base_price_amount": offer.base_price_amount,
            "base_price_credit_in_units": offer.base_price_credit,
            "free_credit_at_start_usage_based": offer.free_credit_at_start,
            "family": offer.family,
            "downpayment": offer.registration_fee
        })

        #register lead
        client = ClientCreator.register_lead(api_client, good_api_key, lead)

        assert 'Welcome to our client family!' in self._get_last_message()

        contract = lead.contract
        initial_repayment_due_time = contract.next_repayment_due_time
        assert contract.get_hours_before_payment_due() == 0
        assert contract.get_cumulative_amount_repaid() == 230000
        assert contract.get_cumulative_amount_repaid(cached=True) == 230000
        assert contract.get_cumulative_amount_repaid_without_deposit() == 0
        assert contract.next_repayment_due_time.date() == (datetime.today() + timedelta(days=7)).date()
        
        # buy some credit
        amount = Decimal(1000)
        user = User.get(username="super_admin@test.com")
        handle_paycash_request(user, amount, contract.linked_device)
        assert contract.get_cumulative_amount_repaid() == 230000 + amount
        assert contract.get_cumulative_amount_repaid(cached=True) == 230000 + amount
        assert contract.next_repayment_due_time.date() == (initial_repayment_due_time + timedelta(days=7)).date()

        #swap device
        new_device = DeviceCreateService.create(serial_number="456", device_type="SOL", mode=1)
        handle_device_change_request(user, contract, new_device)
        assert contract.linked_device == new_device

        #give delay
        handle_give_delay_request(user, client, delayed_days=5, this_device=new_device)
        assert contract.next_repayment_due_time.date() == (initial_repayment_due_time + timedelta(days=7) + timedelta(days=5)).date()

        #give discount unit
        give_discount(user, new_device, discounted_units=1)
        assert contract.next_repayment_due_time.date() == (initial_repayment_due_time + timedelta(days=7) + timedelta(days=5) + timedelta(days=1)).date()

        #give discount amount
        give_discount(user, new_device, discounted_amount=1000)
        assert contract.next_repayment_due_time.date() == (initial_repayment_due_time + timedelta(days=7) + timedelta(days=5) + timedelta(days=8)).date()

        #mark as default
        handle_default_request(user, new_device)
        assert contract.status == ContractStatus.defaulted



    @classmethod
    def _get_last_message(cls):
        last_message = OutgoingSMS.select().order_by(desc(OutgoingSMS.SendingTime)).first()
        return last_message.Body
