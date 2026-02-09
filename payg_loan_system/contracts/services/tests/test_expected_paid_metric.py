

from datetime import datetime, time, timedelta
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from payg_loan_system.transaction_requests.services.change_offer_service import ChangeOfferTransactionService
from payg_loan_system.transaction_requests.services.undo_default_service import UndoDefaultTransactionService
import uuid
from payg_loan_system.transaction_requests.services.default_service import DefaultTransactionService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from freezegun import freeze_time
from mock import patch
from pony.orm import db_session
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.actions.give_delay import handle_give_delay_request
from payg_loan_system.contracts.services.addons.addon_offer_service import (
    AddonOfferService, AddOnLoanExtensionMode, AddOnType)
from payg_loan_system.contracts.services.addon_service import AddonService
from shared.helpers.client_creator import ClientCreator
from shared.helpers.assert_datetime import assert_datetime
from pony.orm import desc


class TestExpectedPaidContractMetric:

    @db_session
    def test_expected_paid_contract_metric_basic(self, api_client, good_api_key):

        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        assert contract.get_expected_amount_repaid() == contract.offer.registration_fee + contract.reference_price

    @db_session
    def test_expected_paid_contract_metric_for_addons(self, api_client, good_api_key, super_admin_user):

        aoffer = AddonOfferService.create(
            super_admin_user(),
            'TestExpectedPaid',
            'TestExpectedPaid',
            '20',
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            need_approval=False,
            available=True,
            loan_mode=AddOnLoanExtensionMode.duration,
            pre_sales=True,
            downpayment='10'
        )

        lead = ClientCreator.create_lead()
        addon = AddonService.create(None, aoffer.last_version, 1, super_admin_user(), lead=lead)
        assert addon.extension_days == 10
        client = ClientCreator.register_lead(api_client, good_api_key, lead, extra_paid=10)
        contract = client.contracts.select().first()
        assert contract.get_expected_amount_repaid() == contract.offer.registration_fee + addon.downpayment + contract.reference_price

        lead = ClientCreator.create_lead()
        addon = AddonService.create(None, aoffer.last_version, 1, super_admin_user(), lead=lead)
        client = ClientCreator.register_lead(api_client, good_api_key, lead, extra_paid=50)
        contract = client.contracts.select().first()

        assert contract.get_expected_amount_repaid() == contract.offer.registration_fee + addon.downpayment + contract.reference_price
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=50)) == 71
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=363)) == 384
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=364)) == 385
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=365)) == 386
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=366)) == 387
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=400)) == 395

        ClientCreator.post_payment({
            "transaction_id": "CompletePayment1",
            "sender_name": "TESTWALLETaddonscomplete",
            "amount": contract.get_outstanding_balance(),
            "memo": contract.reference
        }, api_client, good_api_key)

        assert contract.status == ContractStatus.completed
        assert contract.get_total_value() == 395
        assert contract.get_total_value() == sum(a.total_amount for a in contract.add_ons if a.loan) + contract.offer.get_total_value_with_deposit()
        addon = AddonService.create(contract, aoffer.last_version, 1, super_admin_user())
        assert addon.extension_days == 20
        assert contract.status == ContractStatus.active
        assert contract.get_total_value() == 415
        assert contract.get_total_value() == sum(a.total_amount for a in contract.add_ons if a.loan) + contract.offer.get_total_value_with_deposit()
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=394)) == 415
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=394)) == 415
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=500)) == 415


    @db_session
    def test_expected_paid_contract_metric_with_neg_delay(self, api_client, good_api_key, super_admin_user):

        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()

        base = datetime.now()+timedelta(days=40)
        v = contract.reference_price_at(base)
        with patch.object(Contract, '_get_last_repayment', return_value=contract.repayments.select().order_by(lambda r: desc(r.time)).first()):
            with freeze_time(base):
                with patch.object(Contract, "reference_price_at", return_value=v):
                    with patch.object(Contract, 'update_cached_data'):
                        with patch.object(Contract, 'get_total_loan_addons_value', return_value=0):
                            handle_give_delay_request(super_admin_user(), contract.client, -10, contract.linked_device)
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=39)) == 60
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=40)) == 71

    @db_session
    def test_expected_paid_contract_metric_with_delay(self, api_client, good_api_key, super_admin_user):

        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()

        base = datetime.now()+timedelta(days=40)
        val = contract.reference_price_at(base)
        with patch.object(Contract, '_get_last_repayment', return_value=contract.repayments.select().order_by(lambda r: desc(r.time)).first()):
            with freeze_time(base):
                with patch.object(Contract, "reference_price_at", return_value=val):
                    with patch.object(Contract, 'update_cached_data'):
                        with patch.object(Contract, 'get_total_loan_addons_value', return_value=0):
                            handle_give_delay_request(super_admin_user(), contract.client, 10, contract.linked_device)
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=39)) == 50
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=40)) == 51
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=41)) == 51
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=50)) == 51
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=51)) == 52

    @db_session
    def test_expected_paid_contract_metric_monthly(self, api_client, good_api_key):

        contract = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "TIME_MONTH_EXPECTED_PAID",
            "type": "Time Based",
            "payment_frequency": "MONTHLY"
        }).contracts.select().first()

        assert contract.get_expected_amount_repaid() == 11
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=15)) == 11
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=50)) == 12
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=80)) == 13
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=110)) == 14
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=140)) == 15

        base = datetime(2021, 2, 28)

        client = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "TIME_MONTH_EXPECTED_PAID",
            "type": "Time Based",
            "payment_frequency": "MONTHLY"
        })
        contract = client.contracts.select().first()
        contract.start_time = base
        base = base + timedelta(hours=1)
        assert contract.get_expected_amount_repaid(base) == 11
        assert contract.get_expected_amount_repaid(base+timedelta(days=2)) == 11
        assert contract.get_expected_amount_repaid(base+timedelta(days=27)) == 11
        assert contract.get_expected_amount_repaid(base+timedelta(days=28)) == 12

    @db_session
    def test_expected_paid_contract_metric_after_registration(self, api_client, good_api_key):

        contract = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "EXPECTED_AFTER_REGISTRATION",
            "downpayment": 10,
            "time_to_ownership_in_days": 100,
            "time_given_at_start_in_days": 10,
            "base_price_amount": 1,
            "base_price_time_in_days": 1,
        }).contracts.select().first()

        assert contract.get_expected_amount_repaid() == 10
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=5)) == 10
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=10)) == 11
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=15)) == 16

        contract = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "EXPECTED_AFTER_REGISTRATION2",
            "downpayment": 10,
            "time_to_ownership_in_days": 100,
            "time_given_at_start_in_days": 0,
            "base_price_amount": 1,
            "base_price_time_in_days": 1,
        }).contracts.select().first()

        assert contract.get_expected_amount_repaid() == 11
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=5)) == 16
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=10)) == 21
        assert contract.get_expected_amount_repaid(datetime.now()+timedelta(days=15)) == 26

    @db_session
    def test_expected_paid_contract_metric_for_0s_contracts_and_uncompleted(self, api_client, good_api_key, super_admin_user):

        contract = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "SHORT_TEST_LOAN",
            "downpayment": 1,
            "time_to_ownership_in_days": 10,
            "time_given_at_start_in_days": 1,
            "base_price_amount": 1,
            "base_price_time_in_days": 1,
        }, extra_paid=9).contracts.select().first()

        contract.start_time -= timedelta(days=15)
        contract.next_repayment_due_time = contract.start_time
        for repayment in contract.repayments:
            repayment.time -= timedelta(days=15)
            repayment.next_repayment_due_time -= timedelta(days=15)
        for event in contract.contract_events:
            event.time -= timedelta(days=15)
        contract.end_time -= timedelta(days=15)

        assert contract.status == ContractStatus.completed
        assert contract.start_time <= contract.end_time
        assert_datetime(contract.end_time, contract.start_time)

        assert contract.get_expected_amount_repaid() == 10
        assert contract.get_total_value() == 10
        assert contract.get_total_value(cached=True) == 10
        
        aoffer = AddonOfferService.create(
            super_admin_user(),
            'TestExpectedPaidUncompletion',
            'TestExpectedPaidUncompletion',
            '10',
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            need_approval=False,
            available=True,
            loan_mode=AddOnLoanExtensionMode.duration
        )

        addon = AddonService.create(contract, aoffer.last_version, 1, super_admin_user())
        assert addon.extension_days == 10
        assert contract.end_time is None
        assert_datetime(contract.next_repayment_due_time, addon.time_approved)
        assert contract.get_total_value() == 20
        assert contract.get_total_value(cached=True) == 20
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=5, microseconds=-1)) == 5
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=6, microseconds=-1)) == 6
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=7, microseconds=-1)) == 7
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=9, microseconds=-1)) == 9
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=10, microseconds=-1)) == 10
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=11, microseconds=-1)) == 10
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=13, microseconds=-1)) == 10
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=15, microseconds=-1)) == 10
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=15, minutes=1)) == 11
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=16, minutes=1)) == 12
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=18, minutes=1)) == 14
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=20, minutes=1)) == 16
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=22, minutes=1)) == 18
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=24, minutes=1)) == 20
        assert contract.get_expected_amount_repaid(time=contract.start_time + timedelta(days=25, minutes=1)) == 20

    @db_session
    def test_expected_paid_contract_metric_for_defaulted_contracts(self, api_client, good_api_key, super_admin_user):
        
        contract = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "SHORT_TEST_LOAN"
        }).contracts.select().first()

        assert contract.get_expected_amount_repaid() == 1
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=1)) == 2
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=3)) == 4
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=9)) == 10
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=10)) == 10
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=12)) == 10

        request = DefaultTransactionService.create(
            user=super_admin_user(),
            uuid=str(uuid.uuid1()),
            device_serial=contract.linked_device.composed_serial
        )

        assert request.success

        assert contract.get_expected_amount_repaid() == 1
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=1)) == 1
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=3)) == 1
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=9)) == 1
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=10)) == 1
        assert contract.get_expected_amount_repaid(time=datetime.now()+timedelta(days=12)) == 1

        request = UndoDefaultTransactionService.create(
            user=super_admin_user(),
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            device_serial=contract.linked_device.composed_serial
        )

        assert request.success

        assert contract.get_expected_amount_repaid() == 1
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=1, microseconds=-1)) == 1
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=2, microseconds=-1)) == 2
        # all the deadlines got delayed a few miliseconds (the time that the contract spent defaulted)
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=2, minutes=1)) == 3
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=3, microseconds=-1)) == 3
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=9, microseconds=-1)) == 9
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=10, microseconds=-1)) == 10
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=12, microseconds=-1)) == 10

    @db_session
    def test_expected_paid_contract_metric_for_offer_change_contracts(self, api_client, good_api_key, super_admin_user):
        
        contract = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "SHORT_TEST_LOAN"
        }).contracts.select().first()

        contract.start_time -= timedelta(days=5)
        contract.next_repayment_due_time = contract.start_time
        for repayment in contract.repayments:
            repayment.time -= timedelta(days=5)
            repayment.next_repayment_due_time -= timedelta(days=5)

        ClientCreator.post_payment({
            "transaction_id": "EXPECTEDPAIDWITHCHANGEOFFER",
            "sender_name": "EXPECTEDPAIDWITHCHANGEOFFER",
            "amount": '2',
            "memo": contract.reference
        }, api_client, good_api_key)
        
        request = ChangeOfferTransactionService.create(
            user=super_admin_user(),
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=CreateOfferService.add_from_data_and_user({
                "code": "OFFER_CHANGED_EXPECTED",
                "name": "OFFER_CHANGED_EXPECTED",
                "type": "Loan",
                "downpayment": 2,
                "time_to_ownership_in_days": 20,
                "time_given_at_start_in_days": 0,
                "base_price_amount": 2,
                "raw_unit_cost": '',
                "family": 'Home',
                "base_price_time_in_days": 1,
                "automatic_unlock_code_sending": "True",
                "in_use_for_new_leads": "True",
                "can_be_approved_and_registered": "True"
            }, super_admin_user()).code
        )

        assert request.success, request.answer_data
        assert contract.get_expected_amount_repaid(time=contract.start_time) == 1
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=4, microseconds=1)) == 5
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=5, microseconds=1)) == 6
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=6, microseconds=1)) == 8
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=7, microseconds=1)) == 10
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=8, microseconds=1)) == 12
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=22, microseconds=1)) == 40
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=24, microseconds=1)) == 42

    @db_session
    def test_expected_paid_contract_metric_for_offer_change_contracts_2(self, api_client, good_api_key, super_admin_user):
        
        contract = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "SHORT_TEST_LOAN"
        }).contracts.select().first()

        contract.start_time -= timedelta(days=5)
        contract.next_repayment_due_time = contract.start_time
        for repayment in contract.repayments:
            repayment.time -= timedelta(days=5)
            repayment.next_repayment_due_time -= timedelta(days=5)

        ClientCreator.post_payment({
            "transaction_id": "EXPECTEDPAIDWITHCHANGEOFFER2",
            "sender_name": "EXPECTEDPAIDWITHCHANGEOFFER2",
            "amount": '2',
            "memo": contract.reference
        }, api_client, good_api_key)
        
        request = ChangeOfferTransactionService.create(
            user=super_admin_user(),
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=CreateOfferService.add_from_data_and_user({
                "code": "OFFER_CHANGED_EXPECTED2",
                "name": "OFFER_CHANGED_EXPECTED2",
                "type": "Loan",
                "downpayment": 2,
                "time_to_ownership_in_days": 20,
                "time_given_at_start_in_days": 0,
                "base_price_amount": 1,
                "raw_unit_cost": '',
                "family": 'Home',
                "base_price_time_in_days": 0.5,
                "automatic_unlock_code_sending": "True",
                "in_use_for_new_leads": "True",
                "can_be_approved_and_registered": "True"
            }, super_admin_user()).code
        )

        assert request.success, request.answer_data
        assert contract.get_expected_amount_repaid(time=contract.start_time) == 1
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=4, microseconds=1)) == 5
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=5, microseconds=1)) == 6
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=6, microseconds=1)) == 7
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=7, microseconds=1)) == 9
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=8, microseconds=1)) == 11
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=22, microseconds=1)) == 39
        assert contract.get_expected_amount_repaid(time=contract.start_time+timedelta(days=23, microseconds=1)) == 41
