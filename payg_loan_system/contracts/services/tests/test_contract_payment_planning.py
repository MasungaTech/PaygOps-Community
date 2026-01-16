

from datetime import datetime
from pony.orm import db_session
from shared.helpers.client_creator import ClientCreator


class TestContractPaymentPlanning:

    @db_session
    def test_contract_payment_planning(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "TESTPAYMENTPANNING",
            "name": "TESTPAYMENTPANNING",
            "type": "Loan",
            "downpayment": 10,
            "time_to_ownership_in_days": 10,
            "time_given_at_start_in_days": 1,
            "base_price_amount": 1,
            "raw_unit_cost": '',
            "family": 'Home',
            "base_price_time_in_days": 1,
            "automatic_unlock_code_sending": "True",
            "in_use_for_new_leads": "True",
            "can_be_approved_and_registered": "True"
        })
        contract = client.contracts.select().first()
        table = contract.get_expected_payments_table()
        
        assert sum([row[1] for row in table]) == 19 == table[-1][2] == table[-1][4]
        assert len(table) == 10
