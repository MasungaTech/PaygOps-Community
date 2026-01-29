from pony.orm import flush
from payg_loan_system.actions.undo_deregister import undo_deregister
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


class TestLoanOffers():

    @db_session
    def test_full_loan_journey(self, api_client, good_api_key, super_admin_user):
        #create offer
        offer = CreateOfferService.add_from_data_and_user({
            "code": "TL-123",
            "name": "Test Loan Offer",
            "type": OfferType.loan,
            "downpayment": 230000,
            "free_credit_at_start_loan": 7,
            "base_price_amount": 1000,
            "base_price_time_in_days": 7,
            "family": 'Home',
            "in_use_for_new_leads": "True",
            "can_be_approved_and_registered": "True",
            "time_to_ownership_in_days": 365
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
        new_device = DeviceCreateService.create(serial_number="678", device_type="SOL", mode=1)
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

        #undo default
        undo_deregister(user, contract)
        assert contract.status == ContractStatus.active

        #pay remaining amount
        handle_paycash_request(user, contract.get_outstanding_balance(), contract.linked_device)
        assert contract.status == ContractStatus.completed



    @classmethod
    def _get_last_message(cls):
        last_message = OutgoingSMS.select().order_by(desc(OutgoingSMS.SendingTime)).first()
        return last_message.Body
