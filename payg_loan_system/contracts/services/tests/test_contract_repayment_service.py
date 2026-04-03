import calendar
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from mock import Mock, patch
from pony.orm import db_session, flush, desc


from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.models.repayment_discount_types import \
    ContractRepaymentDiscountTypes
from payg_loan_system.contracts.services.contract_repayment_service import (
    ContractRepaymentService, ContractStatus, Error)
from payg_loan_system.contracts.services.tests.factories import (
    ContractFactory, ContractRepaymentFactory)
from payg_loan_system.offers.models import OfferType
from payg_loan_system.offers.tests.factories import TimeOfferFactory
from payg_loan_system.payments.models.wallet import PaymentWallet
from shared.helpers.assert_datetime import assert_datetime
from shared.helpers.client_creator import ClientCreator
from shared.helpers.date_helper import (DateDifferenceService, add_months,
                                        get_days_in_month, set_day_of_month)
from tests.factories.factories import PaymentFactory, PaymentWalletFactory
from tests.support.mock_query import MockQuery

CREATE_CONTRACT_EVENT_PATH = 'payg_loan_system.contracts.services.contract_repayment_service' +\
                        '.ContractRepaymentService._create_contract_event_object'
CREATE_REPAYMENT_PATH = 'payg_loan_system.contracts.services.contract_repayment_service' + \
                        '.ContractRepaymentService._create_repayment_object'
CREATE_RECONCILED_PATH = 'payg_loan_system.contracts.services.reconciled_payment_service' + \
                        '.ReconciledPaymentService._create_reconciled_payment_object'
GET_SETTINGS_PATH = 'shared.services.settings_service.SettingsService.get_setting'

class FakeRP:

    _repayment = None


    def __init__(self, amount):
        self.amount = amount

    @property
    def repayment(self):
        return self._repayment

    @repayment.setter
    def repayment(self, rp):
        self._repayment = rp
        rp.total_reconciled += self.amount

    def get_serialized_object(self):
        return {}



def _fake_create_reconciled_payment(time, lead=None, addon=None, contract_pending_repayment=None,
                                    user=None, type=None, payment=None, account=None, amount=None, note='', person=None, origin_reconciled_payment=None):
    if contract_pending_repayment:
        contract_pending_repayment.pending_amount = amount
    return FakeRP(amount=amount)


class TestContractRepaymentService:

    def test_not_enough_balance_to_process_payment(self, api_client, good_api_key):
        with db_session:
            client = ClientCreator.create(api_client, good_api_key)
            contract = client.contracts.select().first()
            ClientCreator.post_payment({
                "transaction_id": "NotBalanceTestPayment"+str(client.id),
                "sender_name": "TESTWALLETBALANCENOTENOUGH",
                "amount": '100'
            }, api_client, good_api_key)
        with pytest.raises(Error) as error:
            with db_session:
                wallet = PaymentWallet.get(FullName="TESTWALLETBALANCENOTENOUGH")
                contract = Contract.get(id=contract.id)
                ContractRepaymentService.repay_and_reconcile(contract, account=wallet, amount=200)
        assert error.value.code == 'AMOUNT_OVER_BALANCE'

    @db_session
    def test_payment_between_minimum_and_reference(self, api_client, good_api_key):
        client = ClientCreator.create(api_client, good_api_key, offer_data={
            'code': 'offer_with_minimum',
            'minimum_payment': .5
        })
        contract = client.contracts.select().first()
        assert contract.minimum_payment == 0.5
        assert contract.reference_price == 1
        ClientCreator.post_payment({
            "transaction_id": "TestPaymentOverMinimumBelowReference",
            "sender_name": "TestPaymentOverMinimumBelowReference",
            "amount": '0.7',
            "memo": contract.reference
        }, api_client, good_api_key)
        assert contract.pending_amount == 0
        assert contract.get_cumulative_amount_repaid() == contract.lead.downpayment + Decimal('0.7')

    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_amount_paid_below_offer_minimum(self, *args):
        contract = ContractFactory.stub()
        contract.offer = TimeOfferFactory.stub(base_price_amount=5000)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=100000)
        contract.get_outstanding_balance = Mock(return_value=100000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=1000)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = 1000
        result = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)
        flush()
        assert not result
        assert contract.pending_amount == 1000

    @db_session
    def test_contract_defaulted(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.defaulted
        contract.offer = TimeOfferFactory.stub(base_price_amount=5000)
        contract.get_outstanding_balance_discounted = Mock(return_value=100000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=1000)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = 1000

        with pytest.raises(Error) as error:
            result = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)

        assert 'CONTRACT_DEFAULTED' in str(error)

    @db_session
    def test_contract_completed(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.completed
        contract.offer = TimeOfferFactory.stub(base_price_amount=5000)
        contract.get_outstanding_balance_discounted = Mock(return_value=0)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=1000)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = 1000

        with pytest.raises(Error) as error:
            result = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)

        assert 'CONTRACT_COMPLETED' in str(error)

    @patch(GET_SETTINGS_PATH, return_value=0.1)
    def test_negative_discount_more_than_currently_paid(self, *args):
        contract = ContractFactory.stub(no_addons=True)
        contract.offer = TimeOfferFactory.stub(base_price_amount=5000)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=100000)
        contract.get_outstanding_balance = Mock(return_value=100000)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=500)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=1000)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = -1000

        with pytest.raises(Error) as error:
            contract.addons_price_at = Mock(return_value=0)
            result = ContractRepaymentService.give_amount_discount(contract, amount)

        assert 'NEGATIVE_CONTRACT_BALANCE_FORBIDDEN' in str(error)

    @patch(CREATE_CONTRACT_EVENT_PATH)
    @db_session
    def test_negative_discount_less_than_currently_paid(self, *args):
        contract = ContractFactory.stub()
        contract.offer = TimeOfferFactory.stub(base_price_amount=5000)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=100000)
        contract.get_outstanding_balance = Mock(return_value=100000)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=500)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=1000)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = -400
        repayment = ContractRepaymentFactory.stub(time=datetime.now())
        with patch(CREATE_REPAYMENT_PATH, return_value=repayment):
            result = ContractRepaymentService.give_amount_discount(contract, amount)

        assert result == repayment

    @patch(CREATE_CONTRACT_EVENT_PATH)
    @db_session
    def test_negative_discount_on_completed_undo_status(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.completed
        contract.offer = TimeOfferFactory.stub(base_price_amount=5000)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=0)
        contract.get_outstanding_balance = Mock(return_value=0)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=1000)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        contract.client.contracts = MockQuery([contract])

        amount = -500
        repayment = ContractRepaymentFactory.stub(time=datetime.now())
        with patch(CREATE_REPAYMENT_PATH, return_value=repayment):
            result = ContractRepaymentService.give_amount_discount(contract, amount)

        assert result == repayment
        assert contract.status == ContractStatus.active

    # Test discount exact amount to pay marks completed
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @db_session
    def test_discount_remaining_due_marks_completed(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=5000)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=9999)
        contract.get_outstanding_balance = Mock(return_value=9999)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=9999)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=9999))
        amount = 9999
        repayment = ContractRepaymentFactory.stub(time=datetime.now())
        with patch(CREATE_REPAYMENT_PATH, return_value=repayment):
            result = ContractRepaymentService.give_amount_discount(contract, amount)

        assert result == repayment
        assert contract.status == ContractStatus.completed

    # Test discount more than due refused
    @patch(CREATE_CONTRACT_EVENT_PATH)
    def test_discount_over_due_refused(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=5000)
        contract.get_outstanding_balance_discounted = Mock(return_value=9999)
        contract.get_outstanding_balance = Mock(return_value=9999)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=11000)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=11000))
        amount = 11000
        repayment = ContractRepaymentFactory.stub(time=datetime.now())
        with patch(CREATE_REPAYMENT_PATH, return_value=repayment):
            with pytest.raises(Error) as error:
                result = ContractRepaymentService.give_amount_discount(contract, amount)

        assert 'DISCOUNT_MORE_THAN_LEFT_TO_PAY' in str(error)

    # Test grace period
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @db_session
    def test_grace_period_success(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=5000)
        contract.get_outstanding_balance_discounted = Mock(return_value=9999)
        contract.get_outstanding_balance = Mock(return_value=9999)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        contract.update_cached_data = Mock()
        days = 7
        contract.next_repayment_due_time = datetime.now() + timedelta(days=1)
        last_payment_due_time = contract.next_repayment_due_time
        repayment = ContractRepaymentFactory.stub(time=datetime.now())
        with patch(CREATE_REPAYMENT_PATH, return_value=repayment):
            result = ContractRepaymentService.give_days_grace_period(contract, days)

        assert result == repayment
        assert contract.status == ContractStatus.active
        assert contract.next_repayment_due_time == last_payment_due_time + timedelta(days=7)

    # Test payment exact amount marks complete
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_payment_exact_due_marks_complete(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=9999)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=9999)
        contract.get_outstanding_balance = Mock(return_value=9999)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=9999)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        contract.addons_price_at = lambda *args, **kwargs: 0
        amount = 9999
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]
        assert contract.status == ContractStatus.completed
        assert_datetime(contract.end_time, datetime.now())
        assert repayment.amount == 9999  # Pays exact the amount due
        assert repayment.total_reconciled == 9999

    # Test payment more than due gets split
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_pays_over_due_split(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=9999)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=9999)
        contract.get_outstanding_balance = Mock(return_value=9999)
        contract.addons_price_at = lambda *args, **kwargs: 0
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=11000)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = 11000
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]

        assert contract.status == ContractStatus.completed
        assert_datetime(contract.end_time, datetime.now())
        assert repayment.amount == 9999 # Pays only the amount due, not more
        assert repayment.total_reconciled == 9999

    # Test rounding discount
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_pays_slightly_less_rounding_discount(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=5500)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=9999)
        contract.get_outstanding_balance = Mock(return_value=9999)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        contract.addons_price_at = lambda *args, **kwargs: 0
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=Decimal(9998.95))
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=Decimal(5000)))
        amount = Decimal('9998.95')
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]

        assert contract.status == ContractStatus.completed  # Completed even if slightly below
        assert repayment.total_reconciled == amount


    # Test pays less than minimum to complete
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_pays_less_than_minimum_to_complete_success(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=5500)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=999)
        contract.get_outstanding_balance = Mock(return_value=999)
        contract.addons_price_at = lambda *args, **kwargs: 0
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=109000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=Decimal(999)) # enough to finish paying with rounding
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=Decimal(500)))
        amount = Decimal(999)
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]

        assert contract.status == ContractStatus.completed # Completed even if payment below minimum and slightly below
        assert repayment.total_reconciled == amount

    # Test pays less than minimum to complete (with rounding)
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_pays_less_than_minimum_to_complete_success_with_rounding(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=5500)
        contract.offer_at = lambda t: contract.offer
        contract.get_outstanding_balance_discounted = Mock(return_value=999)
        contract.get_outstanding_balance = Mock(return_value=999)
        contract.addons_price_at = lambda *args, **kwargs: 0
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=109000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=Decimal(998.95))  # enough to finish paying with rounding
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=Decimal(500)))
        amount = Decimal('998.95')
        repayment = ContractRepaymentFactory.stub(time=datetime.now())
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]

        assert contract.status == ContractStatus.completed  # Completed even if payment below minimum and slightly below
        assert repayment.total_reconciled == amount

    # Test proper number of days from offer added and device linked
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_payment_adds_correct_number_of_days(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        # One week, 1000 per day
        contract.offer = TimeOfferFactory.stub(base_price_amount = Decimal(7000))
        contract.offer_at = lambda t: contract.offer
        contract.offer.base_price_credit = Decimal(7)
        contract.get_outstanding_balance_discounted = Mock(return_value=100000)
        contract.get_outstanding_balance = Mock(return_value=100000)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        contract.addons_price_at = lambda *args, **kwargs: 0
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=Decimal(8000))
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = Decimal(8000)
        contract.next_repayment_due_time = datetime.now()
        old_repayment_due_time = contract.next_repayment_due_time
        new_time = old_repayment_due_time + timedelta(days=8)
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]

        assert contract.status == ContractStatus.active # Still active
        assert contract.next_repayment_due_time.replace(microsecond=0, second=0) == new_time.replace(microsecond=0, second=0)
        assert repayment.amount == amount  # creates repayment for correct amount
        assert repayment.total_reconciled == amount # creates repayment for correct amount

    # Check discount
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_payment_adds_correct_discount(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        # One week, 1000 per day
        contract.offer = TimeOfferFactory.stub(base_price_amount = Decimal(7000))
        contract.offer_at = lambda t: contract.offer
        contract.offer.base_price_credit = Decimal(7)
        contract.offer.discount_price_1_amount = Decimal(9000)
        contract.offer.discount_price_1_credit = Decimal(10)
        contract.get_outstanding_balance_discounted = Mock(return_value=100000)
        contract.get_outstanding_balance = Mock(return_value=100000)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        contract.addons_price_at = lambda *args, **kwargs: 0
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=Decimal(9000))
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = Decimal(9000)
        contract.next_repayment_due_time = datetime.now()
        old_repayment_due_time = contract.next_repayment_due_time
        new_time = old_repayment_due_time + timedelta(days=10)
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]

        assert contract.status == ContractStatus.active  # Still active
        assert_datetime(contract.next_repayment_due_time, new_time)
        assert repayment.amount == Decimal(10000)  # creates repayment for correct amount with discount
        assert repayment.amount_paid == Decimal(9000)  # creates repayment for correct amount with discount
        assert repayment.amount_discounted == Decimal(1000)  # creates repayment for correct amount with discount

    # Check late time and late amount stored
    @patch(CREATE_CONTRACT_EVENT_PATH)
    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_payment_adds_correct_late_time(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        # One week, 1000 per day
        contract.offer = TimeOfferFactory.stub(base_price_amount=Decimal(7000))
        contract.offer_at = lambda x: contract.offer
        contract.offer.base_price_credit = Decimal(7)
        contract.get_offer = Mock(return_value=contract.offer)
        contract.get_outstanding_balance_discounted = Mock(return_value=100000)
        contract.get_outstanding_balance = Mock(return_value=100000)
        contract.addons_price_at = lambda *args, **kwargs: 0
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=Decimal(8000))
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = Decimal(8000)
        contract.next_repayment_due_time = datetime.now() - timedelta(days=1)
        new_time = datetime.now() + timedelta(days=8)
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]

        assert contract.status == ContractStatus.active  # Still active
        assert_datetime(contract.next_repayment_due_time, new_time)
        assert repayment.amount == Decimal(8000)  # creates repayment for correct amount with discount
        assert repayment.hours_late == Decimal('24.0001')  # creates repayment for correct amount with discount
        assert repayment.amount_late == Decimal(1000)  # creates repayment for correct amount with discount

    def test_reverse_repayment(self, api_client, good_api_key):
        with db_session:
            client = ClientCreator.create(api_client, good_api_key)
            contract = client.contracts.select().first()
            initial_next_payment = contract.next_repayment_due_time
            ClientCreator.post_payment({
                "transaction_id": "RepaymentTestPayment"+str(client.id),
                "sender_name": client.full_name,
                "sender_msisdn": client.person.contactPhone.number,
                "amount": str(contract.offer.base_price_amount)
            }, api_client, good_api_key)
            repayment = contract.repayments.select()[:][-1]
            ContractRepaymentService.reverse_repayment(repayment)

        with db_session:
            reversed_repayment = contract.repayments.select()[:][-1]
            assert reversed_repayment.converse.id == repayment.id
            reversed_recon = reversed_repayment.reconciled_payments.select().first().converse.id
            recon = repayment.reconciled_payments.select().first().id
            assert reversed_recon == recon
            assert reversed_repayment.discount_type == ContractRepaymentDiscountTypes.reversal
            assert_datetime(repayment.next_repayment_due_time, initial_next_payment+timedelta(
                days=float(contract.offer.base_price_credit)), seconds=5)
            assert_datetime(contract.next_repayment_due_time, initial_next_payment, seconds=5)
            assert contract.repayments.count() == 3
            wallet = repayment.reconciled_payments.select().first().linked_payment.PaymentWallet
            assert wallet.get_balance() == contract.offer.base_price_amount

    def test_reverse_repayment_discount(self, api_client, good_api_key):
        with db_session:
            client = ClientCreator.create(api_client, good_api_key, offer_data={
                "code": "OFFER_WITH_DISCOUNT",
                "base_price_amount": 1,
                "base_price_time_in_days": 1,
                "discount_price_1_amount": 3,
                "discount_price_1_time_in_days": 7
            })
            contract = client.contracts.select().first()
            initial_next_payment = contract.next_repayment_due_time
            paid_already = contract.get_percentage_repaid()
            ClientCreator.post_payment({
                "transaction_id": "RepaymentTestPayment"+str(client.id),
                "sender_name": client.full_name,
                "sender_msisdn": client.person.contactPhone.number,
                "amount": str(contract.offer.discount_price_1_amount)
            }, api_client, good_api_key)
            paid_after_payment = contract.get_percentage_repaid()
            contract = client.contracts.select().first()
            repayment = contract.repayments.select()[:][-1]
            ContractRepaymentService.reverse_repayment(repayment)

        with db_session:
            reversed_repayment = contract.repayments.select()[:][-1]
            assert reversed_repayment.converse.id == repayment.id
            rb = contract.offer.base_price_credit/contract.offer.base_price_amount
            repaid = contract.offer.discount_price_1_credit/rb
            assert round(paid_after_payment, 5) == round(paid_already + repaid/contract.get_total_value(), 5)
            assert paid_already == contract.get_percentage_repaid()
            reversed_recon = reversed_repayment.reconciled_payments.select().first().converse.id
            recon = repayment.reconciled_payments.select().first().id
            assert reversed_recon == recon
            assert reversed_repayment.discount_type == ContractRepaymentDiscountTypes.reversal
            assert_datetime(repayment.next_repayment_due_time, initial_next_payment+timedelta(
                days=float(contract.offer.discount_price_1_credit)), seconds=5)
            assert_datetime(contract.next_repayment_due_time, initial_next_payment, seconds=5)
            assert contract.repayments.count() == 3
            wallet = repayment.reconciled_payments.select().first().linked_payment.PaymentWallet
            assert wallet.get_balance() == contract.offer.discount_price_1_amount

    @db_session
    def test_allows_first_payment_below_minimum_when_day_of_month_specified(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key, offer_data={
            "name": "TEST_DAY_OF_MONTH_TIME_BASED",
            "code": "TEST_DAY_OF_MONTH_TIME_BASED",
            "type": "Time Based",
            "base_price_amount": 1000,
            "base_price_time_in_days": 1,
            "time_given_at_start_in_days": 0,
            "family": "Home",
            "downpayment": 0,
            "payment_frequency": 'MONTHLY',
            "payment_day_of_month": 31
        })
        contract = client.contracts.select().first()
        ClientCreator.post_payment({
            "transaction_id": "TEST_PAYMENT_TEST_DAY_OF_MONTH_TIME_BASED",
            "sender_name": client.full_name,
            "sender_msisdn": client.person.contactPhone.number,
            "amount": "999",
            "memo": contract.reference
        }, api_client, good_api_key)
        days_in_month = get_days_in_month(contract.start_time)
        days_to_pay = DateDifferenceService.number_of_days_in_between(
            contract.start_time, set_day_of_month(contract.start_time, days_in_month)
        ) - 1
        expected_amount_paid = Decimal(
            days_to_pay/days_in_month
        ) * contract.offer.get_base_price_per_credit()
        expected_amount_paid = round(expected_amount_paid, 2)

        repayment = contract.repayments.select().order_by(lambda r: desc(r.id)).first()

        assert contract.next_repayment_due_time.day == days_in_month
        assert contract.next_repayment_due_time.month == datetime.now().month
        assert repayment.amount_paid == expected_amount_paid

    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_adds_correct_number_of_months(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=Decimal(1000))
        contract.offer_at = lambda t: contract.offer
        contract.offer.type = OfferType.time_based
        contract.offer.payment_frequency = 'MONTHLY'
        contract.offer.is_monthly = True
        contract.offer.base_price_credit = Decimal(1)
        contract.offer.discount_price_1_amount = Decimal(9000)
        contract.offer.discount_price_1_credit = Decimal(10)
        contract.get_outstanding_balance_discounted = Mock(return_value=100000)
        contract.get_outstanding_balance = Mock(return_value=100000)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        contract.addons_price_at = lambda *args, **kwargs: 0
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=Decimal(9000))
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = Decimal(9000)
        contract.next_repayment_due_time = datetime.now()
        old_repayment_due_time = contract.next_repayment_due_time
        new_time = add_months(old_repayment_due_time, 10)
        repayment = ContractRepaymentFactory.stub(time=datetime.now())
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]
        diff = (contract.next_repayment_due_time.year - old_repayment_due_time.year) * 12 + contract.next_repayment_due_time.month - old_repayment_due_time.month
        assert diff == 10
        assert contract.status == ContractStatus.active  # Still active
        assert_datetime(contract.next_repayment_due_time, new_time)
        assert repayment.amount == Decimal(10000)  # creates repayment for correct amount with discount
        assert repayment.amount_paid == Decimal(9000)  # creates repayment for correct amount with discount
        assert repayment.amount_discounted == Decimal(1000)  # creates repayment for correct amount with discount

    @patch(CREATE_RECONCILED_PATH, side_effect=_fake_create_reconciled_payment)
    @db_session
    def test_adds_correct_number_of_months_slightly_over_base(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.offer = TimeOfferFactory.stub(base_price_amount=Decimal(1000))
        contract.offer_at = lambda t: contract.offer
        contract.offer.type = OfferType.time_based
        contract.offer.payment_frequency = 'MONTHLY'
        contract.offer.is_monthly = True
        contract.addons_price_at = lambda *args, **kwargs: 0
        contract.offer.base_price_credit = Decimal(1)
        contract.get_outstanding_balance_discounted = Mock(return_value=100000)
        contract.get_outstanding_balance = Mock(return_value=100000)
        contract.get_cumulative_amount_repaid_without_deposit = Mock(return_value=100000)
        account = PaymentWalletFactory.stub()
        account.get_balance = Mock(return_value=Decimal(9000))
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=5000))
        amount = Decimal(1100)
        contract.next_repayment_due_time = datetime.now()
        old_repayment_due_time = contract.next_repayment_due_time
        repayment = ContractRepaymentFactory.stub(time=datetime.now())
        with patch(CREATE_REPAYMENT_PATH, side_effect=ContractRepaymentFactory.stub):
            repayment = ContractRepaymentService.repay_and_reconcile(contract, account=account, amount=amount)[0]
        new_month = add_months(old_repayment_due_time, 1)
        month_days = calendar.monthrange(new_month.year, new_month.month)[1]
        extra_hours = month_days*0.1*24
        new_time = new_month + timedelta(hours=extra_hours)
        assert contract.status == ContractStatus.active  # Still active
        assert_datetime(contract.next_repayment_due_time, new_time)
        assert repayment.amount == Decimal(1100)
        assert repayment.amount_paid == Decimal(1100)
        assert repayment.amount_discounted == Decimal(0)