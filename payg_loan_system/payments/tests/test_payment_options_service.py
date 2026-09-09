from decimal import Decimal
from mock import patch
from pony import orm
import pytest
from sales_system.leads.tests.factories import AbstractLeadFactory
from payg_loan_system.payments.services.payment_options_service import PaymentOptionsService
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService
from payg_loan_system.devices.factories import DeviceAbstractFactory
from shared.helpers.client_creator import ClientCreator


class TestPaymentOptionsService:

    def test_device_no_client(self):
        device = DeviceAbstractFactory.create_no_client()
        options = PaymentOptionsService.get_from_device(device)
        assert options == []

    def test_device_no_offer(self):
        device = DeviceAbstractFactory.create_no_client()
        options = PaymentOptionsService.get_from_device(device)
        assert options == []

    @orm.db_session
    def test_client_no_device(self, api_client, good_api_key):
        client = ClientCreator.create(api_client, good_api_key)
        options = PaymentOptionsService.get_from_client_id(client.id)
        assert options == [
            {
                'contract_reference': client.contracts.select().first().reference,
                'payment_options': [
                    {
                        'pricing_amount': Decimal('1.00'),
                        'pricing_period_in_days': 1,
                        'type': 'REPAYMENT',
                        'max_multiple': Decimal('365'),
                        'currency': 'USD'
                    }
                ]
            }
        ]

    def test_lead_already_paid(self):
        lead = AbstractLeadFactory.create()
        options = PaymentOptionsService.get_from_lead(lead)
        assert options == [
            {
                'contract_reference': 'C88880224',
                'payment_options': []
            }
        ]

    @orm.db_session
    def test_lead_already_awaiting_payment(self):
        lead = AbstractLeadFactory.create()
        lead.already_paid = Decimal(0)
        lead.deposit_paid = False
        options = PaymentOptionsService.get_from_lead(lead)
        assert options == [
            {
                'contract_reference': 'C88880224',
                'payment_options': [
                    {
                        'max_multiple': 1,
                        'pricing_amount': Decimal('10000'),
                        'pricing_period_in_days': 7,
                        'type': 'INITIAL_PAYMENT',
                        'currency': 'USD'
                    }
                ]
            }
        ]

    @patch.object(PaymentOptionsService, 'get_contract_reference_from_device', return_value='C88880224')
    @orm.db_session
    def test_device_with_client(self, *args):
        device = DeviceAbstractFactory.create()
        device.contract.pending_amount = 0
        with patch.object(device.contract, 'get_outstanding_balance', return_value=494000):
            options = PaymentOptionsService.get_from_device(device)
        assert options == [
                            {
                                'contract_reference': 'C88880224',
                                'payment_options': [
                                    {
                                        'max_multiple': Decimal('3'),
                                        'pricing_amount': Decimal('9500'),
                                        'pricing_period_in_days': 7,
                                        'type': 'REPAYMENT',
                                        'currency': 'USD'
                                    },
                                    {
                                        'max_multiple': Decimal('1'),
                                        'pricing_amount': Decimal('38000'),
                                        'pricing_period_in_days': 32,
                                        'type': 'REPAYMENT',
                                        'currency': 'USD'
                                    },
                                    {
                                        'max_multiple': Decimal('8'),
                                        'pricing_amount': Decimal('57000'),
                                        'pricing_period_in_days': 49,
                                        'type': 'REPAYMENT',
                                        'currency': 'USD'
                                    }
                                ]
                            }
        ]

    @patch.object(PaymentOptionsService, 'get_contract_reference_from_device', return_value='C88880224')
    def test_device_with_client_completed(self, *args):
        device = DeviceAbstractFactory.create()
        device.contract.pending_amount = 0
        with patch.object(device.contract, 'get_outstanding_balance', return_value=0):
            options = PaymentOptionsService.get_from_device(device)
        assert options == [
            {
                'contract_reference': 'C88880224',
                'payment_options': []
            }
        ]

    def test_max_multiple_regular(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=1000,
            next_pricing=3000,
            previous_pricing=None,
            amount_left_to_pay=10000
        )
        assert multiple == 2

    def test_max_multiple_regular(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=3000,
            next_pricing=10000,
            previous_pricing=1000,
            amount_left_to_pay=10000
        )
        assert multiple == 3

    def test_max_multiple_fully_paid(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=1000,
            next_pricing=3000,
            previous_pricing=500,
            amount_left_to_pay=0
        )
        assert multiple == 0

    def test_max_multiple_overpaid(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=1000,
            next_pricing=3000,
            previous_pricing=500,
            amount_left_to_pay=-2000
        )
        assert multiple == 0

    def test_max_multiple_almost_fully_paid(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=1000,
            next_pricing=3000,
            previous_pricing=None,
            amount_left_to_pay=1,
        )
        assert multiple == 1

    def test_max_multiple_equal_left_to_pay(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=1000,
            next_pricing=3000,
            previous_pricing=500,
            amount_left_to_pay=3000,
        )
        assert multiple == 2

    def test_max_multiple_equal_left_to_pay_2(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=1000,
            next_pricing=3500,
            previous_pricing=500,
            amount_left_to_pay=3500,
        )
        assert multiple == 3

    def test_amount_left_equals_pricing(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=3500,
            next_pricing=None,
            previous_pricing=1000,
            amount_left_to_pay=3500,
        )
        assert multiple == 1

    def test_amount_left_under_pricing(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=2000,
            next_pricing=None,
            previous_pricing=None,
            amount_left_to_pay=500,
        )
        assert multiple == 1

    def test_amount_left_under_pricing_2(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=2000,
            next_pricing=2500,
            previous_pricing=None,
            amount_left_to_pay=500,
        )
        assert multiple == 1

    def test_can_go_over_amount_left_to_pay_if_next_pricing_too_big(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=2000,
            next_pricing=5000,
            previous_pricing=None,
            amount_left_to_pay=3000,
        )
        assert multiple == 2

    def test_can_go_over_amount_left_to_pay_if_next_pricing_too_big_reciprocal(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=5000,
            next_pricing=None,
            previous_pricing=2000,
            amount_left_to_pay=3000,
        )
        assert multiple == 0

    def test_max_multiple_not_go_over_if_more_than_above(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=2000,
            next_pricing=3500,
            previous_pricing=None,
            amount_left_to_pay=3000,
        )
        assert multiple == 1

    def test_max_multiple_not_go_over_if_more_than_above_2(self, *args):
        multiple = PaymentOptionsService._get_max_multiple(
            pricing=5000,
            next_pricing=None,
            previous_pricing=None,
            amount_left_to_pay=1666.67,
        )
        assert multiple == 1
    
    @orm.db_session
    def test_real_client_payment_options_process(self, api_client, good_api_key):

        BASE_PRICE = 1
        BASE_DAYS = 1
        DIS1_PRICE = BASE_PRICE*2
        DIS1_DAYS = BASE_DAYS*3
        DIS2_PRICE = DIS1_PRICE*2
        DIS2_DAYS = DIS1_DAYS*3
        TOTAL_DAYS = 365

        offer_data = {
            "code": "PAYMENTS_API_OPTIONS_OFFER",
            "name": "PAYMENTS_API_OPTIONS_OFFER",
            "time_to_ownership_in_days": TOTAL_DAYS,
            "time_given_at_start_in_days": 0,
            "base_price_amount": BASE_PRICE,
            "base_price_time_in_days": BASE_DAYS,
            "discount_price_1_amount": DIS1_PRICE,
            "discount_price_1_time_in_days": DIS1_DAYS,
            "discount_price_2_amount": DIS2_PRICE,
            "discount_price_2_time_in_days": DIS2_DAYS
        }
        
        client = ClientCreator.create(api_client, good_api_key, offer_data=offer_data)
        options_base = [ #result before 1st payment
            {
                'contract_reference': client.contracts.select().first().reference,
                'payment_options': [
                    {
                        'currency': 'USD',
                        'max_multiple': Decimal(1),
                        'pricing_amount': Decimal(BASE_PRICE),
                        'pricing_period_in_days': BASE_DAYS,
                        'type': 'REPAYMENT'
                    },
                    {
                        'currency': 'USD',
                        'max_multiple': Decimal(1),
                        'pricing_amount': Decimal(DIS1_PRICE),
                        'pricing_period_in_days': DIS1_DAYS,
                        'type': 'REPAYMENT'
                    },
                    {
                        'currency': 'USD',
                        'max_multiple': Decimal((TOTAL_DAYS)//DIS2_PRICE),
                        'pricing_amount': Decimal(DIS2_PRICE),
                        'pricing_period_in_days': DIS2_DAYS,
                        'type': 'REPAYMENT'
                    }
                ]
            }
        ]

        options = PaymentOptionsService.get_from_client(client)
        assert options == options_base

        ClientCreator.post_payment({
            "transaction_id": "TEST_OPTIONS_PAY1",
            "sender_name": client.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(BASE_PRICE)
        }, api_client, good_api_key)

        options = PaymentOptionsService.get_from_client(client)
        remain = TOTAL_DAYS-BASE_DAYS
        options_base[0]['payment_options'][2]['max_multiple'] = Decimal(remain//DIS2_PRICE)
        assert options == options_base

        ClientCreator.post_payment({
            "transaction_id": "TEST_OPTIONS_PAY2",
            "sender_name": client.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(DIS1_PRICE)
        }, api_client, good_api_key)

        options = PaymentOptionsService.get_from_client(client)
        remain -= DIS1_DAYS
        options_base[0]['payment_options'][2]['max_multiple'] = Decimal(remain//DIS2_PRICE)
        assert options == options_base

        left = DIS2_PRICE*2-2
        pay = round((remain-left)/DIS2_DAYS*DIS2_PRICE, 2)
        ClientCreator.post_payment({
            "transaction_id": "TEST_OPTIONS_PAY3",
            "sender_name": client.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(pay)
        }, api_client, good_api_key)

        options = PaymentOptionsService.get_from_client(client)
        remain = round(remain-pay*DIS2_DAYS/DIS2_PRICE, 2)
        options_base[0]['payment_options'][2]['max_multiple'] = Decimal(1)
        assert options == options_base

        pay = 3.5
        ClientCreator.post_payment({
            "transaction_id": "TEST_OPTIONS_PAY4",
            "sender_name": client.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(pay)
        }, api_client, good_api_key)

        options = PaymentOptionsService.get_from_client(client)
        print('options', options_base)
        del options_base[0]['payment_options'][2]
        del options_base[0]['payment_options'][1]
        remain = round(remain-pay*DIS1_DAYS/DIS1_PRICE, 2)
        options_base[0]['payment_options'][0]['pricing_amount'] = Decimal(remain)
        assert options == options_base


    @orm.db_session
    def test_real_client_payment_options_process_time_based(self, api_client, good_api_key):

        BASE_PRICE = 1
        BASE_DAYS = 1
        DIS1_PRICE = BASE_PRICE*2
        DIS1_DAYS = BASE_DAYS*3
        DIS2_PRICE = DIS1_PRICE*2
        DIS2_DAYS = DIS1_DAYS*3

        offer_data = {
            "code": "PAYMENTS_API_OPTIONS_OFFER_TIME",
            "name": "PAYMENTS_API_OPTIONS_OFFER_TIME",
            "type": "Time Based",
            "time_given_at_start_in_days": 0,
            "base_price_amount": BASE_PRICE,
            "base_price_time_in_days": BASE_DAYS,
            "discount_price_1_amount": DIS1_PRICE,
            "discount_price_1_time_in_days": DIS1_DAYS,
            "discount_price_2_amount": DIS2_PRICE,
            "discount_price_2_time_in_days": DIS2_DAYS
        }
        
        client = ClientCreator.create(api_client, good_api_key, offer_data=offer_data)
        options_base = [ #result before 1st payment
            {
                'contract_reference': client.contracts.select().first().reference,
                'payment_options': [
                    {
                        'currency': 'USD',
                        'max_multiple': None,
                        'pricing_amount': Decimal(BASE_PRICE),
                        'pricing_period_in_days': BASE_DAYS,
                        'type': 'REPAYMENT'
                    },
                    {
                        'currency': 'USD',
                        'max_multiple': None,
                        'pricing_amount': Decimal(DIS1_PRICE),
                        'pricing_period_in_days': DIS1_DAYS,
                        'type': 'REPAYMENT'
                    },
                    {
                        'currency': 'USD',
                        'max_multiple': None,
                        'pricing_amount': Decimal(DIS2_PRICE),
                        'pricing_period_in_days': DIS2_DAYS,
                        'type': 'REPAYMENT'
                    }
                ]
            }
        ]

        options = PaymentOptionsService.get_from_client(client)
        assert options == options_base

        ClientCreator.post_payment({
            "transaction_id": "TEST_OPTIONS_PAY1",
            "sender_name": client.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(BASE_PRICE)
        }, api_client, good_api_key)

        options = PaymentOptionsService.get_from_client(client)
        assert options == options_base

        ClientCreator.post_payment({
            "transaction_id": "TEST_OPTIONS_PAY2",
            "sender_name": client.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(DIS1_PRICE)
        }, api_client, good_api_key)

        options = PaymentOptionsService.get_from_client(client)
        assert options == options_base
