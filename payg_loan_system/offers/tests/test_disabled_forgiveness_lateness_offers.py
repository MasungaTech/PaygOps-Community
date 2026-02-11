from datetime import datetime, timedelta
from shared.helpers.assert_datetime import assert_datetime
from pony.orm import db_session
from shared.helpers.client_creator import ClientCreator
from payg_loan_system.actions.give_delay import handle_give_delay_request
from core_system.users.models.user_model import User


class TestNoForgivenessOffers():

    @db_session
    def test_no_forgiveness_journey(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key, offer_data={
            "name": "TEST_FLOW_NO_FORGIVENESS",
            "code": "TEST_FLOW_NO_FORGIVENESS",
            "type": "Loan",
            "base_price_amount": 2,
            "base_price_time_in_days": 1,
            "time_given_at_start_in_days": 0,
            "family": "Home",
            "downpayment": 0,
            "forgive_lateness": False
        })
        contract = client.contracts.select().first()

        user = User.get(username="super_admin@test.com")
        handle_give_delay_request(user, this_client=client, this_device=contract.linked_device, delayed_days=-10, note='')

        ClientCreator.post_payment({
            "transaction_id": "NoForgivenessPayment1",
            "sender_name": "TESTWALLETNoForgiveness",
            "amount": '4', #2 days
            "memo": contract.reference
        }, api_client, good_api_key)

        assert_datetime(contract.next_repayment_due_time, datetime.now()-timedelta(days=8), seconds=5)