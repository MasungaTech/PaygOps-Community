from core_system.users.models.user_model import User
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.models.contract_model import Contract
from sales_system.lead_generator.model import LeadGenerator
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from sales_system.leads.tests.factories import LeadFactory
from core_system.operational_entities.models import Village
from datetime import datetime, timedelta
from decimal import Decimal
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.models.lead_status import LeadStatus
from payg_loan_system.contracts.models.contract_event_model import ContractEventType
from random import randint
from functools import partial
from sales_system.leads.models.lead import Lead
from tests.support.mock_query import MockQuery
import factory
from pony.orm import db_session
from mock import Mock
from payg_loan_system.offers.tests.factories import TimeOfferFactory
from payg_loan_system.devices.factories import DeviceFactory
from payg_loan_system.offers.models import LoanOffer, Offer, OfferType
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from tests.factories.factories import AbstractClientFactory
from core_system.client.models import Client
from core_system.person.models.person_model import Person
from shared.services.settings_service import SettingsService
from stock_management_system.services.stock_movement_creation_service import StockMovementCreationService, StockStatus



class ContractFactory(factory.Factory):
    class Meta:
        model = Contract

    id = factory.Sequence(lambda n: n)
    reference = 'C88880224'
    start_time = datetime.today()
    end_time = None
    repossession_time = None
    status = 'Active'
    offer = TimeOfferFactory.stub(id=1)
    client = AbstractClientFactory.create()
    next_repayment_due_time = datetime.today()
    lead = LeadFactory.stub()
    linked_device = None
    can_be_completed = True
    usage_based = False
    pending_amount = 0
    pending_reconciled_payments_filtered = MockQuery([])
    repayments = MockQuery([])
    add_ons = MockQuery([])
    contract_events = MockQuery([])
    minimum_payment = 0
    downpayment_fully_paid = True

    @classmethod
    @db_session
    def stub(cls, *args, **kwargs):
        contract = super().stub(*args, **kwargs)
        contract.repayments = ContractRepayment.select(lambda r: False)
        contract._get_last_repayment = Mock(return_value=None)
        if not contract.linked_device:
            contract.linked_device = DeviceFactory.stub(ActiveUntil=datetime.now()+timedelta(days=1), contract=contract)
        contract.get_weeks_progression_dict = Mock(return_value={
            'weeks_paid': 7,
            'days_paid': 3,
            'weeks_to_pay': 52,
            'days_to_pay': 364,
            'remaining_weeks_to_pay': 45,
            'remaining_days_to_pay': 315,
        })
        contract.get_outstanding_balance = Mock(return_value=1000)
        contract.get_outstanding_balance_with_addons = Mock(return_value=1000)
        contract.get_outstanding_balance_discounted = Mock(return_value=1000)
        contract.get_total_value = Mock(return_value=1000)
        contract.get_total_days_to_ownership = Mock(return_value=364)
        contract.get_total_value_with_addons = Mock(return_value=1000)
        contract.get_cumulative_amount_repaid = Mock(return_value=1000)
        contract.get_amount_discounted = Mock(return_value=100)
        contract.get_cumulative_days_in_arrear_until_last_payment = Mock(return_value=0)
        contract.get_total_extended = Mock(return_value=0)
        contract.get_total_value_of_lumpsum_addons = Mock(return_value=0)
        contract.get_cumulative_days_in_arrears = Mock(return_value=0)
        contract.get_timeliness_ratio = Mock(return_value=1)
        contract.get_cumulative_amount_repaid_with_addons = Mock(return_value=1000)
        contract.get_cumulative_amount_repaid_without_deposit = partial(Contract.get_cumulative_amount_repaid_without_deposit, contract)
        contract.update_device_status = partial(Contract.update_device_status, contract)
        contract.pending_reconciled_payment = MockQuery([])
        contract.offer_at = partial(Contract.offer_at, contract)
        contract.add_ons = MockQuery([])
        contract.addons_price_at = lambda *args, **kwargs: Contract.addons_price_at(contract, *args, **kwargs) if contract.add_ons else Decimal(0)
        contract.get_percentage_repaid = Mock(return_value=0.5)
        contract.reference_price_at = lambda *args, **kwargs: Contract.reference_price_at(contract, *args, **kwargs) #partial(Contract.reference_price_at, contract)
        contract.minimum_price_at = partial(Contract.minimum_price_at, contract)
        contract.discount_price_1_at = partial(Contract.discount_price_1_at, contract)
        contract.discount_price_2_at = partial(Contract.discount_price_2_at, contract)
        contract.get_units_from_amount = partial(Contract.get_units_from_amount, contract)
        contract.get_date_of_maturity_without_lateness = Mock(return_value=contract.start_time + timedelta(days=364))
        contract.get_value_of_credit = partial(Contract.get_value_of_credit, contract)
        contract.get_expected_amount_repaid = lambda cached=None, include_date_until=None: (200, datetime.now()) if include_date_until else 200
        contract.get_net_cumulative_amount_in_arrears = Mock(return_value=100)
        contract.update_cached_data = partial(Contract.update_cached_data, contract)
        contract.__class__.contract_terms_cache_update_needed = property(Mock(return_value=True))
        contract.__class__.expected_paid_cache_update_needed = property(Mock(return_value=True))
        contract.__class__.contract_repayment_cache_update_needed = property(Mock(return_value=True))
        contract.__class__.reference_price = property(Contract.reference_price.__get__)
        contract.__class__.discount_price_1 = property(Contract.discount_price_1.__get__)
        contract.__class__.discount_price_2 = property(Contract.discount_price_2.__get__)
        contract.__class__.addons_price = property(Mock(return_value=Decimal(0)))
        contract.get_expected_payments_table = partial(Contract.get_expected_payments_table, contract)
        contract.get_total_days_delays_given = partial(Contract.get_total_days_delays_given, contract)
        contract._get_reference_price_changes= partial(Contract._get_reference_price_changes, contract)
        contract.get_number_installments = Mock(return_value=365)
        contract.next_payment_price = partial(Contract.next_payment_price, contract)
        return contract


class ContractRepaymentFactory(factory.Factory):
    class Meta:
        model = ContractRepayment

    amount = 1000
    amount_paid = 1000
    contract = ContractFactory.stub()

    @classmethod
    def stub(cls, *args, **kwargs):
        repayment = super().stub(*args, **kwargs)
        repayment.total_reconciled = 0
        repayment.orphaned_simple_payment = False
        repayment.contract_event = None
        repayment.get_serialized_object = Mock(return_value={})
        return repayment


class TestContractCreator:

    @classmethod
    def create_test_contract(cls, test_name, type=OfferType.loan, offer=None, create_first_repayment=True, npg_device=False, village=False):
        client_person = Person(
            name=test_name,
            surname=test_name,
            type=1,
            village=village or Village.select().first()
        )
        if not client_person.village:
            raise Exception('Person without village')
        client = Client(
            person=client_person,
            RegistrationDate=datetime.now()
        )
        if not offer:
            offer = LoanOffer(
                type=type,
                name=test_name,
                code=test_name,
                family='Home',
                in_use=True,
                in_use_for_new_clients=True,
                registration_fee=1000,
                time_to_ownership_in_days=10,
                base_price_amount=1000,
                base_price_credit=1
            )

        generator = LeadGenerator.get(id=2)

        contract = Contract(
            reference=test_name,
            start_time=datetime.now(),
            end_time=None,
            repossession_time=None,
            next_repayment_due_time=datetime.now(),
            offer=offer,
            client=client,
            lead=Lead(
                offer=offer,
                person=client.person,
                generator=generator,
                receptionTime=client.RegistrationDate,
                statusUpdate=datetime.now(),
                status=LeadStatus.get_first(StatusCategory.installed)
            )
        )
        if create_first_repayment:
            if npg_device:
                number = randint(1,99999999)
                device = DeviceCreateService.create(
                    serial_number=str(number),
                    device_type='NPG',
                    mode=1,
                )
            else:
                device = DeviceCreateService.create(
                    serial_number=test_name,
                    device_type=list(SettingsService.get_setting('AllDeviceAPIS').keys())[0],
                    mode=1,
                )
            contract.linked_device = device
            StockMovementCreationService.create(
                device.stock_item,
                StockStatus.installed,
                user=None,
                destination_client=contract.client,
                note="[Automatic] Registration",
                manual=False
            )
            contract.contract_events.create(
                time=contract.start_time,
                type=ContractEventType.creation,
                approver=None
            )
            ContractRepaymentService.create_first_repayment_on_contract(
                contract,
                User.get_system_user()
            )
        return contract
