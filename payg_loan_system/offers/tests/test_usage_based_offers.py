from datetime import datetime
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.actions.default import handle_default_request
from payg_loan_system.actions.give_discount import give_discount
from payg_loan_system.actions.give_delay import handle_give_delay_request
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from payg_loan_system.devices.factories import DeviceAbstractFactory
from payg_loan_system.actions.swap_device import handle_device_change_request
from payg_loan_system.actions.collect_cash import handle_paycash_request
from core_system.users.models.user_model import User
from decimal import Decimal

from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from payg_loan_system.offers.models import OfferType
from pony.orm import db_session, desc
from shared.helpers.client_creator import ClientCreator
from messages_system.models.sms_db import OutgoingSMS


class TestUsageBasedOffers():

    @db_session
    def test_usage_based_journey(self, api_client, good_api_key):

        lead = ClientCreator.create_lead(offer_data={
            "name": "TEST_FLOW_USAGE_BASED",
            "code": "TEST_FLOW_USAGE_BASED",
            "type": "Usage Based",
            "credit_unit": "kW",
            "base_price_amount": 2,
            "base_price_credit_in_units": 1,
            "free_credit_at_start_usage_based": 0,
            "family": "Home",
            "downpayment": 0
        })

        client = ClientCreator.register_lead(api_client, good_api_key, lead, {'allowed_units': ["kW"]})

        assert 'Welcome to our client family!' in self._get_last_message()

        contract = lead.contract
        assert contract.get_hours_before_payment_due() is None
        assert contract.get_total_extended() == 0
        assert contract.get_total_extended(cached=True) == 0
        assert contract.get_total_value() is None
        assert contract.get_total_value(cached=True) is None
        assert contract.get_yearly_value() is None
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
        assert contract.get_expected_amount_repaid() is None
        assert contract.get_percentage_repaid() is None
        assert contract.get_percentage_repaid(cached=True) is None
        assert contract.get_expected_percentage_repaid() is None
        assert contract.get_timeliness_ratio() is None
        assert contract.get_weeks_progression_dict() is None
        assert contract.get_total_value_of_lumpsum_addons() == 0
        assert contract.get_total_value_of_lumpsum_addons(cached=True) == 0
        assert contract.get_value_of_lumpsum_addons_discounts() == 0
        assert contract.get_value_of_lumpsum_addons_paid_without_discount() == 0
        assert contract.get_date_last_current() is None
        assert contract.get_date_last_in_arrears() is None
        assert contract.get_number_of_non_null_repayments() == 0
        assert contract.get_cumulative_days_in_arrears() is None
        assert contract.get_net_cumulative_days_in_arrears() is None
        assert contract.get_days_in_arrears_since_last_payment() is None
        assert contract.get_amount_in_arrears_since_last_payment() is None
        assert contract.get_net_cumulative_amount_in_arrears() is None
        assert contract.get_cumulative_amount_in_arrears() is None
        assert contract.get_number_of_times_lease_entered_arrears() is None
        assert contract.get_date_of_maturity_without_lateness() is None
        assert contract.get_date_of_maturity() is None
        assert contract.get_default_amount() is None
        assert contract.get_gogla_default_date() is None

    @db_session
    def test_full_usage_based_journey(self, api_client, good_api_key, super_admin_user):
        #create offer
        offer = CreateOfferService.add_from_data_and_user({
            "code": "TUB-123",
            "name": "Test Usage Based Offer",
            "type": OfferType.usage_based,
            "downpayment": 230000,
            "credit_unit": "kW",
            "free_credit_at_start_usage_based": 100,
            "base_price_amount": 100,
            "base_price_credit_in_units": 1,
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
        client = ClientCreator.register_lead(api_client, good_api_key, lead, {'allowed_units': ["kW"]})

        assert 'Welcome to our client family!' in self._get_last_message()

        contract = lead.contract
        initial_repayment_due_time = contract.next_repayment_due_time
        assert contract.get_hours_before_payment_due() is None
        assert contract.get_cumulative_amount_repaid() == 230000
        assert contract.get_cumulative_amount_repaid(cached=True) == 230000
        assert contract.get_cumulative_amount_repaid_without_deposit() == 0
        assert contract.get_credits_bought() == 100
        
        # buy some credit
        amount = Decimal(100)
        user = User.get(username="super_admin@test.com")
        handle_paycash_request(user, amount, contract.linked_device)

        assert contract.get_cumulative_amount_repaid() == 230000 + amount
        assert contract.get_cumulative_amount_repaid(cached=True) == 230000 + amount
        assert contract.get_credits_bought() == 101

        #swap device
        new_device = DeviceCreateService.create(serial_number="123", device_type="SOL", mode=2, allowed_units=["kW"])
        handle_device_change_request(user, contract, new_device)

        assert contract.linked_device == new_device

        #give delay
        give_delay_answer = handle_give_delay_request(user, client, delayed_days=5, this_device=new_device)
        assert give_delay_answer[0]['status'] == 'CREDIT_UNIT_NOT_ALLOWED_FOR_DEVICE'
        assert contract.next_repayment_due_time == initial_repayment_due_time

        #give discount unit
        give_discount(user, new_device, discounted_units=1)
        assert contract.get_credits_bought() == 102

        #give discount amount
        give_discount(user, new_device, discounted_amount=100)
        assert contract.get_credits_bought() == 103

        #mark as default
        handle_default_request(user, new_device)
        assert contract.status == ContractStatus.defaulted


    @classmethod
    def _get_last_message(cls):
        last_message = OutgoingSMS.select().order_by(desc(OutgoingSMS.SendingTime)).first()
        return last_message.Body
