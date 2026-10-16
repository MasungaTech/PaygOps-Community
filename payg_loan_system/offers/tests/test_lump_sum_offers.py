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


class TestLumpSumOffers():

    @db_session
    def test_full_lump_sum_journey(self, api_client, good_api_key, super_admin_user):
        #create offer
        offer = CreateOfferService.add_from_data_and_user({
            "code": "TLS-123",
            "name": "Test Lump Sum Offer",
            "type": OfferType.lump_sum,
            "base_price_amount_lump_sum": 100000,
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
        assert contract is not None
        assert client is not None
        assert contract.get_hours_before_payment_due() is None
        assert contract.get_cumulative_amount_repaid() == 100000
        assert contract.get_cumulative_amount_repaid(cached=True) == 100000
        assert contract.get_cumulative_amount_repaid_without_deposit() == 0
        assert contract.next_repayment_due_time.date() == datetime.today().date()
        assert contract.status == ContractStatus.completed

    @classmethod
    def _get_last_message(cls):
        last_message = OutgoingSMS.select().order_by(desc(OutgoingSMS.SendingTime)).first()
        return last_message.Body
