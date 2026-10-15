from datetime import datetime, timedelta
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from payg_loan_system.transaction_requests.services.undo_default_service import UndoDefaultTransactionService
import uuid
from payg_loan_system.transaction_requests.services.default_service import DefaultTransactionService
from pony import orm
from decimal import Decimal
import pytest
from payg_loan_system.offers.models import LoanOffer
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator
from payg_loan_system.contracts.services.tests.factories import TestContractCreator
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.models.addons_model import AddOnType, AddOnLoanExtensionMode
from payg_loan_system.contracts.services.addons.addon_offer_service import AddonOfferService
from payg_loan_system.contracts.services.contract_metric_service import IndividualContractMetricMixin
from shared.helpers.assert_datetime import assert_datetime
from shared.logger.loggers import Error


class TestContractMetricsService:

    @orm.db_session
    def test_metrics_after_no_repayments(self, api_client, good_api_key, super_admin_user, *args):
        offer = LoanOffer(
            name='test_metrics_after_no_repayments_1',
            code='test_metrics_after_no_repayments_1',
            family='Home',
            in_use=True,
            in_use_for_new_clients=True,
            registration_fee=1000,
            time_to_ownership_in_days=10,
            base_price_amount=1000,
            base_price_credit=1
        )
        client = ClientCreator.create(api_client, good_api_key, offer_data={
            'code': 'test_metrics_after_no_repayments_1'
        })
        contract = client.contracts.select().first()
        contract.start_time -= timedelta(hours=1)
        contract.next_repayment_due_time -= timedelta(hours=1)
        for r in contract.repayments:
            r.time -= timedelta(hours=1)
            r.next_repayment_due_time -= timedelta(hours=1)
        orm.flush()
        assert contract.get_total_value() == Decimal(11000)  # 1000 + 10 * 1000
        assert contract.get_total_value(cached=True) == Decimal(11000)  # 1000 + 10 * 1000
        assert contract.get_cumulative_amount_repaid() == Decimal(1000)  # 1000 registration
        assert contract.get_cumulative_amount_repaid(cached=True) == Decimal(1000)  # 1000 registration
        assert contract.get_cumulative_amount_repaid_without_deposit() == Decimal(0)
        assert contract.get_amount_discounted() == Decimal(0)
        assert contract.get_amount_discounted(cached=True) == Decimal(0)
        assert contract.get_amount_paid_without_discount() == Decimal(1000)
        assert contract.get_outstanding_balance() == Decimal(10000)  # 11000 - 1000
        assert contract.get_outstanding_balance(cached=True) == Decimal(10000)  # 11000 - 1000
        assert contract.get_outstanding_balance_discounted() == Decimal(10000)  # 11000 - 1000
        assert contract.get_outstanding_balance_discounted(cached=True) == Decimal(10000)  # 11000 - 1000
        assert contract.get_expected_amount_repaid() == Decimal(2000)  # The deposit +  first payment
        assert contract.get_expected_amount_repaid(cached=True) == Decimal(2000)  # The deposit +  first payment
        assert contract.get_expected_oustanding_balance() == Decimal(9000)  # 11000 - 2000
        assert round(contract.get_percentage_repaid(), 2) == round(Decimal(1000 / 11000), 2)
        assert round(contract.get_percentage_repaid(cached=True), 2) == round(Decimal(1000 / 11000), 2)
        assert round(contract.get_expected_percentage_repaid(), 2) == round(Decimal(2000 / 11000), 2)
        assert round(contract.get_timeliness_ratio(), 3) == Decimal(0) # All bad
        assert contract.get_weeks_progression_dict() == {
            'weeks_paid': 0,
            'days_paid': 0,
            'weeks_to_pay': 1,
            'days_to_pay': 10,
            'remaining_weeks_to_pay': 1,
            'remaining_days_to_pay': 10,
        }
        assert contract.get_date_last_current().replace(microsecond=0, second=0) == contract.start_time.replace(microsecond=0, second=0)
        assert contract.get_date_last_in_arrears().replace(microsecond=0, second=0) == datetime.now().replace(microsecond=0, second=0)
        assert contract.get_number_of_non_null_repayments() == 1
        assert round(contract.get_cumulative_days_in_arrears(), 4) == round(Decimal(1/24), 4)
        assert round(contract.get_net_cumulative_days_in_arrears(), 4) == round(Decimal(1/24), 4)
        assert round(contract.get_days_in_arrears_since_last_payment(), 4) == round(Decimal(1 / 24), 4)
        assert round(contract.get_amount_in_arrears_since_last_payment(), 4) == 1000
        assert round(contract.get_net_cumulative_amount_in_arrears(), 4) == 1000
        assert round(contract.get_cumulative_amount_in_arrears(), 4) == 1000
        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert contract.get_date_of_maturity_without_lateness() == contract.start_time + timedelta(days=10)
        assert_datetime(contract.get_date_of_maturity(), contract.start_time + timedelta(days=10, hours=1), seconds=3)
        assert round(contract.get_average_days_between_payments(), 2) == round(Decimal(1/24), 2)

        request = DefaultTransactionService.create(
            user=super_admin_user(),
            uuid=str(uuid.uuid1()),
            device_serial=contract.linked_device.composed_serial
        )

        assert request.success
        assert contract.get_amount_in_arrears_since_last_payment() == Decimal('1000')

        request = UndoDefaultTransactionService.create(
            user=super_admin_user(),
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            device_serial=contract.linked_device.composed_serial
        )

        assert request.success
        assert contract.get_amount_in_arrears_since_last_payment() == Decimal('1000')

    @orm.db_session
    def test_metrics_after_one_payment_1(self, api_client, good_api_key, super_admin_user, *args):
        offer = LoanOffer(
            name='test_metrics_after_one_payment_1',
            code='test_metrics_after_one_payment_1',
            family='Home',
            in_use=True,
            in_use_for_new_clients=True,
            registration_fee=1000,
            time_to_ownership_in_days=10,
            base_price_amount=1000,
            base_price_credit=1
        )
        client = ClientCreator.create(api_client, good_api_key, offer_data={
            'code': 'test_metrics_after_one_payment_1'
        })
        contract = client.contracts.select().first()
        repayment = ContractRepaymentService.give_amount_discount(contract, 2000)
        orm.commit()
        assert contract.get_total_extended() == Decimal(0)
        assert contract.get_total_extended(cached=True) == Decimal(0)
        assert IndividualContractMetricMixin.get_total_extended_days(contract) == Decimal(0)
        assert contract.get_total_days_to_ownership() == Decimal(10)
        assert contract.get_total_days_to_ownership(cached=True) == Decimal(10)
        assert contract.get_total_value_without_deposit() == Decimal(10000)
        assert contract.get_total_value() == Decimal(11000) # 1000 + 10 * 1000
        assert contract.get_total_value(cached=True) == Decimal(11000) # 1000 + 10 * 1000
        assert contract.get_cumulative_amount_repaid() == Decimal(3000) # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid(cached=True) == Decimal(3000) # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid_without_deposit() == Decimal(2000)
        assert contract.get_amount_discounted() == Decimal(2000)
        assert contract.get_amount_discounted(cached=True) == Decimal(2000)
        assert contract.get_amount_paid_without_discount() == Decimal(1000)
        assert contract.get_outstanding_balance() == Decimal(8000) # 11000 - 3000
        assert contract.get_outstanding_balance(cached=True) == Decimal(8000) # 11000 - 3000
        assert contract.get_outstanding_balance_discounted() == Decimal(8000) # 11000 - 3000, same here as there is nd discount on that offer
        assert contract.get_outstanding_balance_discounted(cached=True) == Decimal(8000) # 11000 - 3000, same here as there is nd discount on that offer
        assert round(contract.get_expected_amount_repaid(), 3) == Decimal(2000) # The deposit +  first payment
        assert round(contract.get_expected_amount_repaid(cached=True), 3) == Decimal(2000) # The deposit +  first payment
        assert round(contract.get_expected_oustanding_balance(), 3) == Decimal(9000) # 11000 - 2000
        assert round(contract.get_percentage_repaid(), 2) == round(Decimal(3000/11000), 2)
        assert round(contract.get_percentage_repaid(cached=True), 2) == round(Decimal(3000/11000), 2)
        assert round(contract.get_expected_percentage_repaid(), 2) == round(Decimal(2000/11000), 2)
        assert contract.get_weeks_progression_dict() == {
            'weeks_paid': 0,
            'days_paid': 2,
            'weeks_to_pay': 1,
            'days_to_pay': 10,
            'remaining_weeks_to_pay': 1,
            'remaining_days_to_pay': 8
        }
        assert IndividualContractMetricMixin.get_days_paid(contract) == Decimal(2)
        assert IndividualContractMetricMixin.get_days_to_pay(contract) == Decimal(10)
        assert contract.get_date_last_current().replace(microsecond=0, second=0) == datetime.now().replace(microsecond=0, second=0)
        assert contract.get_date_last_in_arrears() == repayment.time
        assert contract.get_number_of_non_null_repayments() == 2
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert contract.get_cumulative_days_in_arrears() <= Decimal('0.0004')/Decimal('24')
        assert contract.get_cumulative_days_in_arrears() > Decimal('0')
        assert round(contract.get_net_cumulative_days_in_arrears(), 4) == Decimal(-1)
        assert round(contract.get_days_in_arrears_since_last_payment(), 4) == -1
        # 2000 paid at last payment - 1000 required
        assert round(contract.get_amount_in_arrears_since_last_payment(), 2) == Decimal('-2000')
        assert round(contract.get_net_cumulative_amount_in_arrears(), 3) == 0
        assert round(contract.get_cumulative_amount_in_arrears(), 3) == Decimal('1000')
        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert contract.get_date_of_maturity_without_lateness() == contract.start_time + timedelta(days=10)
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert_datetime(contract.start_time + timedelta(days=10), contract.get_date_of_maturity(), hours=0.0004)
        assert round(contract.get_average_days_between_payments(), 2) == 0

        request = DefaultTransactionService.create(
            user=super_admin_user(),
            uuid=str(uuid.uuid1()),
            device_serial=contract.linked_device.composed_serial
        )

        assert request.success
        assert contract.get_amount_in_arrears_since_last_payment() == Decimal('-2000')

    @orm.db_session
    def test_metrics_after_one_payment_and_lumpsum_addon(self, super_admin_user, api_client, good_api_key):
        offer = LoanOffer(
            name='test_metrics_after_one_payment_and_lumpsum_addon',
            code='test_metrics_after_one_payment_and_lumpsum_addon',
            family='Home',
            in_use=True,
            in_use_for_new_clients=True,
            registration_fee=1000,
            time_to_ownership_in_days=10,
            base_price_amount=1000,
            base_price_credit=1
        )
        user = super_admin_user()
        client = ClientCreator.create(api_client, good_api_key, offer_data={
            'code': 'test_metrics_after_one_payment_and_lumpsum_addon'
        })
        contract = client.contracts.select().first()
        repayment = ContractRepaymentService.give_amount_discount(contract, 2000)
        addon_offer = AddonOfferService.create(
            user,
            name='test_addon_metric_lump_sum',
            code='TAM1',
            price=1000,
            category=AddOnCategory.get(name="Product"),
            type=AddOnType.lump_sum,
            available=True
        )
        addon = AddonService.create(
            contract=contract,
            offer_version=addon_offer.last_version,
            quantity_sold=1,
            sale_made_by=User.get(username='super_admin@test.com')
        )
        print([u.username for u in User.select()])
        AddonService.pay_with_cash(addon, User.get(username='super_admin@test.com'))
        orm.commit()
        assert contract.get_total_extended() == Decimal(0)
        assert contract.get_total_extended(cached=True) == Decimal(0)
        assert IndividualContractMetricMixin.get_total_extended_days(contract) == Decimal(0)
        assert contract.get_total_days_to_ownership() == Decimal(10)
        assert contract.get_total_days_to_ownership(cached=True) == Decimal(10)
        assert contract.get_total_value_without_deposit() == Decimal(10000)
        assert contract.get_total_value() == Decimal(11000)  # 1000 + 10 * 1000
        assert contract.get_total_value(cached=True) == Decimal(11000)  # 1000 + 10 * 1000
        assert contract.get_cumulative_amount_repaid() == Decimal(3000)  # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid(cached=True) == Decimal(3000)  # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid_without_deposit() == Decimal(2000)
        assert contract.get_amount_discounted() == Decimal(2000)
        assert contract.get_amount_discounted(cached=True) == Decimal(2000)
        assert contract.get_amount_paid_without_discount() == Decimal(1000)
        assert contract.get_outstanding_balance() == Decimal(8000)  # 11000 - 3000
        assert contract.get_outstanding_balance_discounted() == Decimal(
            8000)  # 11000 - 3000, same here as there is nd discount on that offer
        assert round(contract.get_expected_amount_repaid(), 2) == Decimal(2000)  # The deposit +  first payment
        assert round(contract.get_expected_oustanding_balance(), 2) == Decimal(9000)  # 11000 - 2000
        assert round(contract.get_percentage_repaid(), 2) == round(Decimal(3000 / 11000), 2)
        assert round(contract.get_percentage_repaid(cached=True), 2) == round(Decimal(3000 / 11000), 2)
        assert round(contract.get_expected_percentage_repaid(), 2) == round(Decimal(2000 / 11000), 2)
        assert contract.get_weeks_progression_dict() == {
            'weeks_paid': 0,
            'days_paid': 2,
            'weeks_to_pay': 1,
            'days_to_pay': 10,
            'remaining_weeks_to_pay': 1,
            'remaining_days_to_pay': 8
        }
        assert IndividualContractMetricMixin.get_days_paid(contract) == Decimal(2)
        assert IndividualContractMetricMixin.get_days_to_pay(contract) == Decimal(10)
        assert contract.get_date_last_current().replace(microsecond=0, second=0) == datetime.now().replace(
            microsecond=0, second=0)
        assert contract.get_date_last_in_arrears() == repayment.time
        assert contract.get_number_of_non_null_repayments() == 2
        assert contract.get_cumulative_days_in_arrears() <= Decimal('0.0004')/Decimal('24')
        assert contract.get_cumulative_days_in_arrears() > Decimal('0')
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert round(contract.get_net_cumulative_days_in_arrears(), 2) == Decimal(-1)
        assert round(contract.get_days_in_arrears_since_last_payment(), 2) == -1
        # 2000 paid at last payment - 1000 required
        assert round(contract.get_amount_in_arrears_since_last_payment(), 2) == Decimal('-2000')
        assert round(contract.get_net_cumulative_amount_in_arrears(), 2) == 0
        assert round(contract.get_cumulative_amount_in_arrears(), 2) == Decimal('1000')
        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert contract.get_date_of_maturity_without_lateness() == contract.start_time + timedelta(days=10)
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert_datetime(contract.start_time + timedelta(days=10), contract.get_date_of_maturity(), hours=0.01)
        assert round(contract.get_average_days_between_payments(), 2) == 0
        assert contract.get_total_value_of_lumpsum_addons() == Decimal(1000)
        assert contract.get_total_value_of_lumpsum_addons(cached=True) == Decimal(1000)
        assert contract.get_value_of_lumpsum_addons_discounts() == Decimal(0)
        assert contract.get_value_of_lumpsum_addons_paid_without_discount() == Decimal(1000)

    @orm.db_session
    def test_metrics_after_one_payment_and_addon(self, super_admin_user, api_client, good_api_key):
        offer = LoanOffer(
            name='test_metrics_after_one_payment_and_addon',
            code='test_metrics_after_one_payment_and_addon',
            family='Home',
            in_use=True,
            in_use_for_new_clients=True,
            registration_fee=1000,
            time_to_ownership_in_days=10,
            base_price_amount=1000,
            base_price_credit=1
        )
        client = ClientCreator.create(api_client, good_api_key, offer_data={
            'code': 'test_metrics_after_one_payment_and_addon'
        })
        contract = client.contracts.select().first()
        repayment = ContractRepaymentService.give_amount_discount(contract, 2000)
        addon_offer = AddonOfferService.create(
            super_admin_user(),
            name='test_addon_metric_loan',
            code='TAM2',
            price=1000,
            category=AddOnCategory.get(name="Product"),
            type=AddOnType.loan,
            available=True
        )
        addon = AddonService.create(
            contract=contract,
            offer_version=addon_offer.last_version,
            quantity_sold=1,
            sale_made_by=User.get(username='super_admin@test.com'),
            loan_mode=AddOnLoanExtensionMode.duration
        )
        orm.commit()
        assert contract.get_total_extended() == Decimal(1000)
        assert contract.get_total_extended(cached=True) == Decimal(1000)
        assert IndividualContractMetricMixin.get_total_extended_days(contract) == Decimal(1)
        assert contract.reference_price == 1000
        assert contract.get_total_days_to_ownership() == Decimal(11)
        assert contract.get_total_days_to_ownership(cached=True) == Decimal(11)
        assert contract.get_total_value_without_deposit() == Decimal(11000)
        assert contract.get_total_value() == Decimal(12000)  # 1000 + 10 * 1000 + 1000 addon
        assert contract.get_total_value(cached=True) == Decimal(12000)  # 1000 + 10 * 1000 + 1000 addon
        assert contract.get_cumulative_amount_repaid() == Decimal(3000)  # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid(cached=True) == Decimal(3000)  # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid_without_deposit() == Decimal(2000)
        assert contract.get_amount_discounted() == Decimal(2000)
        assert contract.get_amount_discounted(cached=True) == Decimal(2000)
        assert contract.get_amount_paid_without_discount() == Decimal(1000)
        assert contract.get_outstanding_balance() == Decimal(9000)  # 11000 + 1000 - 3000
        assert contract.get_outstanding_balance_discounted() == Decimal(
            9000)  # 11000 - 3000, same here as there is nd discount on that offer
        assert round(contract.get_expected_amount_repaid(), 2) == Decimal(2000)  # The deposit +  first payment
        assert round(contract.get_expected_oustanding_balance(), 2) == Decimal(10000)  # 11000 + 1000 - 2000
        assert round(contract.get_percentage_repaid(), 2) == round(Decimal(3000 / 12000), 2)
        assert round(contract.get_percentage_repaid(cached=True), 2) == round(Decimal(3000 / 12000), 2)
        assert round(contract.get_expected_percentage_repaid(), 2) == round(Decimal(2000 / 12000), 2)
        assert contract.get_weeks_progression_dict() == {
            'weeks_paid': 0,
            'days_paid': 2,
            'weeks_to_pay': 2,
            'days_to_pay': 11,
            'remaining_weeks_to_pay': 1,
            'remaining_days_to_pay': 9
        }
        assert IndividualContractMetricMixin.get_days_paid(contract) == Decimal(2)
        assert IndividualContractMetricMixin.get_days_to_pay(contract) == Decimal(11)
        assert contract.get_date_last_current().replace(microsecond=0, second=0) == datetime.now().replace(
            microsecond=0, second=0)
        assert contract.get_date_last_in_arrears() == repayment.time
        assert contract.get_number_of_non_null_repayments() == 2
        assert contract.get_cumulative_days_in_arrears() <= Decimal('0.0004')/Decimal('24')
        assert contract.get_cumulative_days_in_arrears() > Decimal('0')
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert round(contract.get_net_cumulative_days_in_arrears(), 2) == Decimal(-1)
        assert round(contract.get_days_in_arrears_since_last_payment(), 2) == -1
        # 2000 paid at last payment - 1000 required
        assert round(contract.get_amount_in_arrears_since_last_payment(), 2) == Decimal('-2000')
        assert round(contract.get_net_cumulative_amount_in_arrears(), 2) == 0
        assert round(contract.get_cumulative_amount_in_arrears(), 2) == Decimal('1000')
        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert contract.get_date_of_maturity_without_lateness() == contract.start_time + timedelta(days=11)
        assert_datetime(contract.start_time + timedelta(days=11), contract.get_date_of_maturity(), hours=0.0004)
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert round(contract.get_average_days_between_payments(), 2) == 0

    @orm.db_session
    def test_metrics_after_one_payment_and_addon_repayment_increase(self, super_admin_user, api_client, good_api_key):
        offer = LoanOffer(
            name='test_metrics_after_one_payment_and_addon_repayment_increase',
            code='test_metrics_after_one_payment_and_addon_repayment_increase',
            family='Home',
            in_use=True,
            in_use_for_new_clients=True,
            registration_fee=1000,
            time_to_ownership_in_days=10,
            base_price_amount=1000,
            base_price_credit=1
        )
        client = ClientCreator.create(api_client, good_api_key, offer_data={
            'code': 'test_metrics_after_one_payment_and_addon_repayment_increase'
        })
        contract = client.contracts.select().first()
        repayment = ContractRepaymentService.give_amount_discount(contract, 2000)
        addon_offer = AddonOfferService.create(
            super_admin_user(),
            name='test_addon_metric_loan_repayment',
            code='TAM3',
            price=1000,
            category=AddOnCategory.get(name="Product"),
            type=AddOnType.loan,
            available=True
        )
        addon = AddonService.create(
            contract=contract,
            offer_version=addon_offer.last_version,
            quantity_sold=1,
            sale_made_by=User.get(username='super_admin@test.com'),
            loan_mode=AddOnLoanExtensionMode.amount
        )
        orm.commit()
        assert contract.get_total_extended() == Decimal(1000)
        assert contract.get_total_extended(cached=True) == Decimal(1000)
        assert IndividualContractMetricMixin.get_total_extended_days(contract) == Decimal(0)
        assert contract.reference_price == 1000+1000/8 # the discount equals 2 repayments, 10-2=8
        assert contract.get_total_days_to_ownership() == Decimal(10)
        assert contract.get_total_days_to_ownership(cached=True) == Decimal(10)
        assert contract.get_total_value_without_deposit() == Decimal(11000)
        assert contract.get_total_value() == Decimal(12000)  # 1000 + 10 * 1000 + 1000 addon
        assert contract.get_total_value(cached=True) == Decimal(12000)  # 1000 + 10 * 1000 + 1000 addon
        assert contract.get_cumulative_amount_repaid() == Decimal(3000)  # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid(cached=True) == Decimal(3000)  # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid_without_deposit() == Decimal(2000)
        assert contract.get_amount_discounted() == Decimal(2000)
        assert contract.get_amount_discounted(cached=True) == Decimal(2000)
        assert contract.get_amount_paid_without_discount() == Decimal(1000)
        assert contract.get_outstanding_balance() == Decimal(9000)  # 11000 + 1000 - 3000
        assert contract.get_outstanding_balance_discounted() == Decimal(
            9000)  # 11000 - 3000, same here as there is nd discount on that offer
        assert round(contract.get_expected_amount_repaid(), 2) == Decimal(2000)  # The deposit +  first payment (first one is before addon)
        assert round(contract.get_expected_oustanding_balance(), 2) == Decimal(10000)  # 11000 + 1000 - 2000
        assert round(contract.get_percentage_repaid(), 2) == round(Decimal(3000 / 12000), 2)
        assert round(contract.get_percentage_repaid(cached=True), 2) == round(Decimal(3000 / 12000), 2)
        assert round(contract.get_expected_percentage_repaid(), 2) == round(Decimal(2000 / 12000), 2)
        assert contract.get_weeks_progression_dict() == {
            'weeks_paid': 0,
            'days_paid': 2,
            'weeks_to_pay': 1,
            'days_to_pay': 10,
            'remaining_weeks_to_pay': 1,
            'remaining_days_to_pay': 8
        }
        assert IndividualContractMetricMixin.get_days_paid(contract) == Decimal(2)
        assert IndividualContractMetricMixin.get_days_to_pay(contract) == Decimal(10)
        assert contract.get_date_last_current().replace(microsecond=0, second=0) == datetime.now().replace(
            microsecond=0, second=0)
        assert contract.get_date_last_in_arrears() == repayment.time
        assert contract.get_number_of_non_null_repayments() == 2
        assert contract.get_cumulative_days_in_arrears() <= Decimal('0.0004')/Decimal('24')
        assert contract.get_cumulative_days_in_arrears() > Decimal('0')
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert round(contract.get_net_cumulative_days_in_arrears(), 2) == Decimal(-1)
        assert round(contract.get_days_in_arrears_since_last_payment(), 2) == -1
        # 2000 paid at last payment - 1000 required
        assert round(contract.get_amount_in_arrears_since_last_payment(), 2) == Decimal('-2000')
        assert round(contract.get_net_cumulative_amount_in_arrears(), 1) == 0
        assert round(contract.get_cumulative_amount_in_arrears(), 1) == Decimal('1000')
        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert contract.get_date_of_maturity_without_lateness() == contract.start_time + timedelta(days=10)
        assert_datetime(contract.start_time + timedelta(days=10), contract.get_date_of_maturity(), hours=0.0004)
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert round(contract.get_average_days_between_payments(), 2) == 0

    @orm.db_session
    def test_metrics_after_completed(self, api_client, good_api_key):
        offer = LoanOffer(
            name='test_metrics_after_completed',
            code='test_metrics_after_completed',
            family='Home',
            in_use=True,
            in_use_for_new_clients=True,
            registration_fee=1000,
            time_to_ownership_in_days=10,
            base_price_amount=1000,
            base_price_credit=1
        )
        client = ClientCreator.create(api_client, good_api_key, offer_data={
            'code': 'test_metrics_after_completed'
        })
        contract = client.contracts.select().first()
        repayment = ContractRepaymentService.give_amount_discount(contract, 10000)
        orm.flush()
        assert contract.get_total_value() == Decimal(11000)  # 1000 + 10 * 1000
        assert contract.get_total_value(cached=True) == Decimal(11000)  # 1000 + 10 * 1000
        assert contract.get_cumulative_amount_repaid() == Decimal(11000)  # 1000 registration + 10000
        assert contract.get_cumulative_amount_repaid(cached=True) == Decimal(11000)  # 1000 registration + 10000
        assert contract.get_cumulative_amount_repaid_without_deposit() == Decimal(10000)
        assert contract.get_amount_discounted() == Decimal(10000)
        assert contract.get_amount_discounted(cached=True) == Decimal(10000)
        assert contract.get_amount_paid_without_discount() == Decimal(1000)
        assert contract.get_outstanding_balance() == Decimal(0)  # 11000 - 11000
        assert contract.get_outstanding_balance_discounted() == Decimal(0)  # 11000 - 11000, same here as there is nd discount on that offer
        assert contract.get_expected_amount_repaid() == Decimal(2000)  # The deposit +  first payment
        assert contract.get_expected_oustanding_balance() == Decimal(9000)  # 11000 - 2000
        assert round(contract.get_percentage_repaid(), 2) == 1
        assert round(contract.get_percentage_repaid(cached=True), 2) == 1
        assert round(contract.get_expected_percentage_repaid(), 2) == Decimal('0.18')
        assert contract.get_weeks_progression_dict() == {
            'weeks_paid': 1,
            'days_paid': 3,
            'weeks_to_pay': 1,
            'days_to_pay': 10,
            'remaining_weeks_to_pay': 0,
            'remaining_days_to_pay': 0,
        }
        assert_datetime(contract.get_date_last_current(), datetime.now())
        assert contract.get_date_last_in_arrears() == repayment.time
        assert contract.get_number_of_non_null_repayments() == 2
        assert contract.get_cumulative_days_in_arrears() <= Decimal('0.0004')/Decimal('24')
        assert contract.get_cumulative_days_in_arrears() > Decimal('0')
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert contract.get_net_cumulative_days_in_arrears() <= Decimal('0.0004')/Decimal('24')
        assert contract.get_net_cumulative_days_in_arrears() > Decimal('0')
        assert round(contract.get_days_in_arrears_since_last_payment() or 0, 2) == 0
        assert round(contract.get_amount_in_arrears_since_last_payment(), 2) == Decimal('-10000')
        assert round(contract.get_net_cumulative_amount_in_arrears(), 2) == 0
        assert round(contract.get_cumulative_amount_in_arrears(), 2) == Decimal('1000')
        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert contract.get_date_of_maturity_without_lateness() == contract.start_time + timedelta(days=10)
        assert contract.get_date_of_maturity() == contract.end_time
        assert round(contract.get_average_days_between_payments(), 2) == 0

    @orm.db_session
    def test_metrics_after_one_payment_and_delay(self, api_client, good_api_key, *args):
        offer = LoanOffer(
            name='test_metrics_after_one_payment_and_delay',
            code='test_metrics_after_one_payment_and_delay',
            family='Home',
            in_use=True,
            in_use_for_new_clients=True,
            registration_fee=1000,
            time_to_ownership_in_days=10,
            base_price_amount=1000,
            base_price_credit=1
        )
        client = ClientCreator.create(api_client, good_api_key, offer_data={
            'code': 'test_metrics_after_one_payment_and_delay'
        })
        contract = client.contracts.select().first()
        contract.start_time = datetime.now() - timedelta(seconds=1)
        repayment = ContractRepaymentService.give_amount_discount(contract, 2000)
        delay = ContractRepaymentService.give_days_grace_period(contract, 3)
        orm.commit()
        assert contract.get_total_extended() == Decimal(0)
        assert contract.get_total_extended(cached=True) == Decimal(0)
        assert IndividualContractMetricMixin.get_total_extended_days(contract) == Decimal(0)
        assert contract.get_total_days_to_ownership() == Decimal(10)
        assert contract.get_total_days_to_ownership(cached=True) == Decimal(10)
        assert contract.get_total_value_without_deposit() == Decimal(10000)
        assert contract.get_total_value() == Decimal(11000)  # 1000 + 10 * 1000
        assert contract.get_total_value(cached=True) == Decimal(11000)  # 1000 + 10 * 1000
        assert contract.get_cumulative_amount_repaid() == Decimal(3000)  # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid(cached=True) == Decimal(3000)  # 1000 registration + 2000
        assert contract.get_cumulative_amount_repaid_without_deposit() == Decimal(2000)
        assert contract.get_amount_discounted() == Decimal(2000)
        assert contract.get_amount_discounted(cached=True) == Decimal(2000)
        assert contract.get_amount_paid_without_discount() == Decimal(1000)
        assert contract.get_outstanding_balance() == Decimal(8000)  # 11000 - 3000
        assert contract.get_outstanding_balance_discounted() == Decimal(8000)  # 11000 - 3000, same here as there is nd discount on that offer
        assert round(contract.get_expected_amount_repaid(), 3) == Decimal(2000)  # The deposit +  first payment
        assert round(contract.get_expected_oustanding_balance(), 3) == Decimal(9000)  # 11000 - 2000
        assert round(contract.get_percentage_repaid(), 2) == round(Decimal(3000 / 11000), 2)
        assert round(contract.get_percentage_repaid(cached=True), 2) == round(Decimal(3000 / 11000), 2)
        assert round(contract.get_expected_percentage_repaid(), 2) == round(Decimal(2000 / 11000), 2)
        assert contract.get_weeks_progression_dict() == {
            'weeks_paid': 0,
            'days_paid': 2,
            'weeks_to_pay': 1,
            'days_to_pay': 10,
            'remaining_weeks_to_pay': 1,
            'remaining_days_to_pay': 8
        }
        assert IndividualContractMetricMixin.get_days_paid(contract) == Decimal(2)
        assert IndividualContractMetricMixin.get_days_to_pay(contract) == Decimal(10)
        assert contract.get_date_last_current().replace(microsecond=0, second=0) == datetime.now().replace(
            microsecond=0, second=0)
        assert contract.get_date_last_in_arrears() == repayment.time
        assert contract.get_number_of_non_null_repayments() == 2
        assert contract.get_cumulative_days_in_arrears() <= Decimal('0.0004')/Decimal('24')
        assert contract.get_cumulative_days_in_arrears() > Decimal('0')
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert round(contract.get_net_cumulative_days_in_arrears(), 4) == Decimal('-4')
        assert round(contract.get_days_in_arrears_since_last_payment(), 4) == Decimal('-4')
        # 2000 paid at last payment - 1000 required 
        assert round(contract.get_amount_in_arrears_since_last_payment(), 3) == Decimal('-2000')
        assert round(contract.get_net_cumulative_amount_in_arrears(), 3) == 0
        assert round(contract.get_cumulative_amount_in_arrears(), 3) == Decimal('1000')
        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert contract.get_date_of_maturity_without_lateness() == contract.start_time + timedelta(days=10)
        assert_datetime(contract.get_date_of_maturity(), contract.start_time + timedelta(days=10+3), hours=0.0005) # 10 + 3 days of delays
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert round(contract.get_average_days_between_payments(), 2) == 0

    @orm.db_session
    def test_contract_metrics_with_lead_addons(self, api_client, good_api_key):

        user = User.get(username="super_admin@test.com")
        lead = ClientCreator.create_lead(offer_data={
            'name': 'test_contract_metrics_with_lead_addons',
            'code': 'test_contract_metrics_with_lead_addons',
            'downpayment': 1000,
            'time_to_ownership_in_days': 10,
            'base_price_amount': 1000,
            'base_price_credit': 1
        })
        doffer = AddonOfferService.create(
            user,
            'TestMetricsAddonsToLeadDuration',
            'TestMetricsAddonsToLeadDuration',
            '2000',
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            need_approval=False,
            available=True,
            loan_mode=AddOnLoanExtensionMode.duration,
            pre_sales=True,
            downpayment='1000'
        )
        roffer = AddonOfferService.create(
            user,
            'TestMetricsAddonsToLeadRepayment',
            'TestMetricsAddonsToLeadRepayment',
            '2000',
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            need_approval=False,
            available=True,
            loan_mode=AddOnLoanExtensionMode.amount,
            pre_sales=True,
            downpayment='1000'
        )
        daddon = AddonService.create(None, doffer.last_version, 1, user, lead=lead)
        raddon = AddonService.create(None, roffer.last_version, 1, user, lead=lead)

        client = ClientCreator.register_lead(api_client, good_api_key, lead, extra_paid=4000)
        contract = client.contracts.select().first()

        # repayment = ContractRepaymentService.give_amount_discount(contract, 2000)
        orm.commit()
        assert contract.get_total_extended() == Decimal(2000)
        assert contract.get_total_extended(cached=True) == Decimal(2000)
        assert IndividualContractMetricMixin.get_total_extended_days(contract) == Decimal(1)
        assert contract.reference_price == Decimal(str(round(1000 + 1000/11, 2))) # the discount equals 2 repayments, 10-2=8
        assert contract.get_total_days_to_ownership() == Decimal(11)
        assert contract.get_total_days_to_ownership(cached=True) == Decimal(11)
        assert contract.get_total_value_without_deposit() == Decimal(12000)
        assert contract.get_total_value() == Decimal(15000)  # 3000 + 10 * 1000
        assert contract.get_total_value(cached=True) == Decimal(15000)  # 3000 + 10 * 1000
        assert contract.get_cumulative_amount_repaid() == Decimal(5000)
        assert contract.get_cumulative_amount_repaid(cached=True) == Decimal(5000)
        # 1000 first registration attempt + 1000 offer registration + 4000 extra (2000 addons downpayment + 2000 repaid (1.83 repayments))
        assert contract.get_cumulative_amount_repaid_without_deposit() == Decimal(2000)
        assert contract.get_amount_discounted() == Decimal(0)
        assert contract.get_amount_paid_without_discount() == Decimal(5000)
        assert contract.get_outstanding_balance() == Decimal(10000)  # 15000 - 6000
        assert contract.get_outstanding_balance_discounted() == Decimal(10000)  # 15000 - 6000, same here as there is nd discount on that offer
        assert round(contract.get_expected_amount_repaid(), 3) == Decimal(3000) + contract.reference_price  # The deposit +  first payment
        assert round(contract.get_expected_oustanding_balance(), 3) == Decimal(12000) - contract.reference_price  # 15000 - paid
        assert round(contract.get_percentage_repaid(), 2) == round(Decimal(5000 / 15000), 2)
        assert round(contract.get_percentage_repaid(cached=True), 2) == round(Decimal(5000 / 15000), 2)
        assert round(contract.get_expected_percentage_repaid(), 2) == round(Decimal((3000 + contract.reference_price) / 15000), 2)
        assert contract.get_weeks_progression_dict() == {
            'weeks_paid': 0,
            'days_paid': 2,
            'weeks_to_pay': 2,
            'days_to_pay': 11,
            'remaining_weeks_to_pay': 1,
            'remaining_days_to_pay': 9
        }
        assert round(IndividualContractMetricMixin.get_days_paid(contract), 2) == Decimal('1.83') # 1.83 = 2000 repaid at 1090.91 per day (1000 + 1000/11)
        assert IndividualContractMetricMixin.get_days_to_pay(contract) == Decimal(11)
        assert contract.get_date_last_current().replace(microsecond=0, second=0) == datetime.now().replace(
            microsecond=0, second=0)
        assert contract.get_date_last_in_arrears() == None
        assert contract.get_number_of_non_null_repayments() == 2
        assert contract.get_cumulative_days_in_arrears() == 0
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        arrears = Decimal(str(-round(2000-contract.reference_price, 2)))
        days_arrears = Decimal(str(round(arrears/contract.reference_price, 2)))
        assert round(contract.get_net_cumulative_days_in_arrears(), 2) == days_arrears
        assert round(contract.get_days_in_arrears_since_last_payment(), 2) == days_arrears
        assert round(contract.get_amount_in_arrears_since_last_payment(), 3) == contract.reference_price
        assert round(contract.get_net_cumulative_amount_in_arrears(), 3) == 0
        assert contract.get_cumulative_amount_in_arrears() == 0
        assert contract.get_number_of_times_lease_entered_arrears() == 0
        assert contract.get_date_of_maturity_without_lateness() == contract.start_time + timedelta(days=11)
        assert_datetime(contract.start_time + timedelta(days=11), contract.get_date_of_maturity(), hours=0.0004)
        # 0.0001 is the lateness resolution, assumed the discount arrives less than 36 seconds after registration
        assert round(contract.get_average_days_between_payments(), 2) == 0

    @orm.db_session
    def test_contract_metrics_with_lead_duration_addons(self, api_client, good_api_key):

        user = User.get(username="super_admin@test.com")
        lead = ClientCreator.create_lead(offer_data={
            'name': 'test_contract_metrics_with_lead_addons_duration',
            'code': 'test_contract_metrics_with_lead_addons_duration',
            'downpayment': 1000,
            'time_to_ownership_in_days': 10,
            'base_price_amount': 1000,
            'base_price_credit': 1
        })
        aoffer = AddonOfferGetterService.get_from_user_and_properties(user, code="ADD_ONE_DAY")
        with pytest.raises(Error) as error:
            addon = AddonService.create(None, aoffer.last_version, 10, user, lead=lead)
        assert error.value.code == 'OFFER_NOT_AVAILABLE_FOR_LEADS'
        aoffer.last_version.available_for_sales = True
        aoffer.last_version.available_for_registration = True
        aoffer.need_approval = False
        addon = AddonService.create(None, aoffer.last_version, 10, user, lead=lead)

        client = ClientCreator.register_lead(api_client, good_api_key, lead)
        contract = client.contracts.select().first()

        # repayment = ContractRepaymentService.give_amount_discount(contract, 2000)
        orm.commit()
        assert contract.get_total_extended() == Decimal(0)
        assert contract.get_total_extended(cached=True) == Decimal(0)
        assert IndividualContractMetricMixin.get_total_extended_days(contract) == Decimal(10)
        assert contract.reference_price == Decimal(str(round(1000 - 10000/20, 2)))
        assert contract.get_total_days_to_ownership() == Decimal(20)
        assert contract.get_total_days_to_ownership(cached=True) == Decimal(20)
        assert contract.get_total_value_without_deposit() == Decimal(10000)
        assert contract.get_total_value() == Decimal(11000)  # 3000 + 10 * 1000
        assert contract.get_total_value(cached=True) == Decimal(11000)  # 3000 + 10 * 1000
        assert contract.get_cumulative_amount_repaid() == Decimal(1000)
        assert contract.get_cumulative_amount_repaid(cached=True) == Decimal(1000)
        # 1000 first registration attempt + 1000 offer registration + 4000 extra (2000 addons downpayment + 2000 repaid)
        assert contract.get_cumulative_amount_repaid_without_deposit() == Decimal(0)
        assert contract.get_amount_discounted() == Decimal(0)
        assert contract.get_amount_paid_without_discount() == Decimal(1000)
        assert contract.get_outstanding_balance() == Decimal(10000) 
        assert contract.get_outstanding_balance_discounted() == Decimal(10000)  # same here as there is nd discount on that offer
        assert round(contract.get_expected_amount_repaid(), 3) == Decimal(1000) + contract.reference_price  # The deposit +  first payment
        assert round(contract.get_expected_oustanding_balance(), 3) == Decimal(10000) - contract.reference_price 
        assert round(contract.get_percentage_repaid(), 2) == round(Decimal(1000 / 11000), 2)
        assert round(contract.get_percentage_repaid(cached=True), 2) == round(Decimal(1000 / 11000), 2)
        assert round(contract.get_expected_percentage_repaid(), 2) == round(Decimal((1000 + contract.reference_price) / 11000), 2)
        assert contract.get_weeks_progression_dict() == {
            'weeks_paid': 0,
            'days_paid': 0,
            'weeks_to_pay': 3,
            'days_to_pay': 20,
            'remaining_weeks_to_pay': 3,
            'remaining_days_to_pay': 20
        }
        assert IndividualContractMetricMixin.get_days_paid(contract) == Decimal(0)
        assert IndividualContractMetricMixin.get_days_to_pay(contract) == Decimal(20)
        assert_datetime(contract.get_date_last_current(), datetime.now(), seconds=60)
        assert contract.get_number_of_non_null_repayments() == 1
        days_arrears = Decimal(str(round((datetime.now()-contract.start_time).total_seconds()/3600/24, 2)))
        assert round(contract.get_net_cumulative_days_in_arrears(), 2) == days_arrears
        assert round(contract.get_days_in_arrears_since_last_payment(), 2) == days_arrears
        assert round(contract.get_amount_in_arrears_since_last_payment(), 3) == contract.reference_price
        assert round(contract.get_net_cumulative_amount_in_arrears(), 3) == contract.reference_price
        assert contract.get_cumulative_amount_in_arrears() == contract.reference_price
        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert round(contract.get_average_days_between_payments(), 2) == 0

    @orm.db_session
    def test_contract_timeliness_ratio(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key)
        contract = client.contracts.select().first()
        contract.start_time = datetime.now()-timedelta(days=3)
        contract.next_repayment_due_time = contract.start_time
        downrepayment = contract.repayments.select().first()
        downrepayment.time = contract.start_time
        downrepayment.next_repayment_due_time = contract.start_time

        assert contract.get_number_of_times_lease_entered_arrears() == 1
        assert contract.get_timeliness_ratio() == 0

        ClientCreator.post_payment({
            "transaction_id": "TEST_PAYMENT_TIMELINESS_RATIO",
            "sender_name": contract.client.full_name,
            "sender_msisdn": contract.client.person.contactPhone.number,
            "amount": "2",
            "memo": contract.reference
        }, api_client, good_api_key)

        repayment = contract.repayments.select().order_by(lambda r: orm.desc(r.time)).first()
        repayment.time = contract.start_time + timedelta(days=1)
        repayment.hours_late = Decimal(24)
        repayment.next_repayment_due_time = contract.start_time + timedelta(days=3)
        contract.next_repayment_due_time = repayment.next_repayment_due_time

        assert round(contract.get_timeliness_ratio(), 4) == Decimal('0.6667')

