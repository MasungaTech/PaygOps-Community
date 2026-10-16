from decimal import Decimal
from pony.orm import db_session
from shared.helpers.client_creator import ClientCreator
from payg_loan_system.actions.collect_cash import handle_paycash_request
from core_system.users.models.user_model import User


class TestContractDisabledProRata:

    @db_session
    def test_disabled_pro_rata(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "DISABLED_PRO_RATA",
            "name": "DISABLED_PRO_RATA",
            'allow_pro_rata': False,
            'base_price_amount': 1,
            'base_price_time_in_days': 1,
            'discount_price_1_amount': 5,
            'discount_price_1_time_in_days': 6,
            'discount_price_2_amount': 10,
            'discount_price_2_time_in_days': 15,
        })
        user = User.get(username="super_admin@test.com")
        contract = client.contracts.select().first()
        device = contract.linked_device

        answer = handle_paycash_request(user, 2, device)
        assert answer[0]['status'] == 'CASH_PAYMENT_SUCCESS_CLIENT'
        assert answer[1]['status'] == 'PAYMENT_RECEIVED'
        assert answer[2]['status'] == 'ACTIVATION_TIME_BOUGHT'
        assert answer[2]['activation_answer_code'] == '123 456 789'
        assert answer[2]['amount_paid'] == 2
        assert answer[2]['days_bought'] == 2
        assert answer[2]['hours_bought'] == 0

        assert contract.repayments.count() == 3
        assert contract.repayments.select()[:][1].amount == 1
        assert contract.repayments.select()[:][2].amount == 1
        assert contract.pending_amount == 0

        answer = handle_paycash_request(user, 2.5, device)
        assert answer[0]['status'] == 'CASH_PAYMENT_SUCCESS_CLIENT'
        assert answer[1]['status'] == 'PAYMENT_RECEIVED'
        assert answer[2]['status'] == 'ACTIVATION_TIME_BOUGHT'
        assert answer[2]['amount_paid'] == 2
        assert answer[2]['days_bought'] == 2
        assert answer[2]['hours_bought'] == 0
        assert answer[2]['activation_answer_code'] == '123 456 789'
        assert answer[3]['status'] == 'BALANCE_INSUFFICIENT_LOAN'
        assert answer[3]['balance'] == 0.5
        assert contract.repayments.count() == 5
        assert contract.repayments.select()[:][3].amount_paid == 1
        assert contract.repayments.select()[:][4].amount_paid == 1
        assert contract.pending_amount == 0.5

        answer = handle_paycash_request(user, 6, device)
        assert answer[0]['status'] == 'CASH_PAYMENT_SUCCESS_CLIENT'
        assert answer[1]['status'] == 'PAYMENT_RECEIVED'
        assert answer[2]['status'] == 'ACTIVATION_TIME_BOUGHT'
        assert answer[2]['amount_paid'] == 6
        assert answer[2]['days_bought'] == 7
        assert answer[2]['hours_bought'] == 0
        assert answer[2]['activation_answer_code'] == '123 456 789'
        assert contract.repayments.count() == 7
        assert contract.repayments.select()[:][5].amount_paid == 5
        assert contract.repayments.select()[:][6].amount_paid == 1
        assert contract.pending_amount == 0.5

        answer = handle_paycash_request(user, 15, device)
        assert answer[0]['status'] == 'CASH_PAYMENT_SUCCESS_CLIENT'
        assert answer[1]['status'] == 'PAYMENT_RECEIVED'
        assert answer[2]['status'] == 'ACTIVATION_TIME_BOUGHT'
        assert answer[2]['amount_paid'] == 15
        assert answer[2]['days_bought'] == 21
        assert answer[2]['hours_bought'] == 0
        assert answer[2]['activation_answer_code'] == '123 456 789'
        assert contract.repayments.count() == 9
        assert contract.repayments.select()[:][7].amount_paid == 10
        assert contract.repayments.select()[:][8].amount_paid == 5
        assert contract.pending_amount == 0.5

        answer = handle_paycash_request(user, 27.7, device)
        assert answer[0]['status'] == 'CASH_PAYMENT_SUCCESS_CLIENT'
        assert answer[1]['status'] == 'PAYMENT_RECEIVED'
        assert answer[2]['status'] == 'ACTIVATION_TIME_BOUGHT'
        assert answer[2]['amount_paid'] == 28
        assert answer[2]['days_bought'] == 39
        assert answer[2]['hours_bought'] == 0
        assert answer[2]['activation_answer_code'] == '123 456 789'
        assert answer[3]['status'] == 'BALANCE_INSUFFICIENT_LOAN'
        assert answer[3]['balance'] == Decimal('0.2')
        assert contract.repayments.count() == 15
        assert contract.repayments.select()[:][9].amount_paid == 10
        assert contract.repayments.select()[:][10].amount_paid == 10
        assert contract.repayments.select()[:][11].amount_paid == 5
        assert contract.repayments.select()[:][12].amount_paid == 1
        assert contract.repayments.select()[:][13].amount_paid == 1
        assert contract.repayments.select()[:][13].amount_paid == 1


    @db_session
    def test_disabled_pro_rata_first_payment_several_bundles(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "DISABLED_PRO_RATA2",
            "name": "DISABLED_PRO_RATA2",
            'allow_pro_rata': False,
            'downpayment': 10,
            'time_given_at_start_in_days': 10,
            'base_price_amount': 1,
            'base_price_time_in_days': 1,
            'discount_price_1_amount': None,
            'discount_price_1_time_in_days': None,
            'discount_price_2_amount': None,
            'discount_price_2_time_in_days': None,
        }, extra_paid=5)
        contract = client.contracts.select().first()
        assert contract.repayments.count() == 6
        assert sum([r.amount for r in contract.repayments]) == 15