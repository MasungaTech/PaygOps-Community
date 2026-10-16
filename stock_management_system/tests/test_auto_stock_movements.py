from datetime import datetime
from random import randint

from pony import orm

from core_system.core_entities import db
from core_system.users.models.user_model import User
from payg_loan_system.actions.swap_device import handle_device_change_request
from payg_loan_system.contracts.services.contract_creation_service import \
    ContractCreationService
from payg_loan_system.contracts.services.contract_termination_service import \
    ContractTerminationService
from payg_loan_system.contracts.services.contract_undo_termination_service import \
    ContractUndoTerminationService
from payg_loan_system.contracts.services.tests.factories import \
    TestContractCreator
from payg_loan_system.devices.services.create_device_service import \
    DeviceCreateService
from payg_loan_system.offers.models import LoanOffer
from payg_loan_system.payments.services.payment_creation_service import \
    PaymentCreationService
from payg_loan_system.payments.services.reconciliation_service import \
    ReconciliationService
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.edit_lead_service import EditLeadService
from stock_management_system.models import StockStatus
from stock_management_system.services.stock_item_getter_service import \
    StockItemGetterService
from stock_management_system.services.stock_movement_creation_service import \
    StockMovementCreationService
from tests.factories import user_mock


class TestAutomaticStockMovements:

    @orm.db_session
    def _get_user(self):
        this_username = 'test@movementguy1.com'
        this_user = User.get(username=this_username)
        if not this_user:
            this_user = user_mock.create_user('Test', 'MovementGuy1', this_username, '+2348882223334', role_name='SuperAdmin')
            orm.flush()
        return this_user

    @orm.db_session
    def _get_agent(self):
        this_username = 'test@movementguy2.com'
        this_user = User.get(username=this_username)
        if not this_user:
            this_user = user_mock.create_user('Test', 'MovementGuy2', this_username, '+2348882227334',
                                              role_name='Agent')
            orm.flush()
        return this_user

    @orm.db_session
    def _new_npg_device(self):
        number = randint(1, 99999999)
        device = DeviceCreateService.create(
            serial_number=str(number),
            device_type='NPG',
            mode=1,
        )
        return device

    @orm.db_session
    def test_device_swap(self):
        user = self._get_user()
        village = user.shop.children.select().first().children.select().first()
        contract = TestContractCreator.create_test_contract('test_device_swap_movement_1', npg_device=True, village=village)
        client = contract.client
        assert user.can_access('SwapDeviceActions', person=client.person), client.person.village
        old_device = contract.linked_device
        new_device = self._new_npg_device()
        result = handle_device_change_request(
            user,
            contract,
            new_device
        )
        orm.flush()

        print(result)
        assert old_device.stock_item.status == StockStatus.with_user
        assert old_device.stock_item.user == user
        assert old_device.stock_item.client == None
        assert new_device.stock_item.status == StockStatus.installed
        assert new_device.stock_item.client == client
        assert new_device.stock_item.user == None

    @orm.db_session
    def test_device_swap_not_visible_does_not_fail(self):
        contract = TestContractCreator.create_test_contract(
            'test_device_swap_movement_2',
            npg_device=True
        )
        client = contract.client
        old_device = contract.linked_device
        new_device = self._new_npg_device()
        StockMovementCreationService.create(
            new_device.stock_item, StockStatus.in_stock,
            destination_entity=db.Hub.get(name='Shop2'), manual=False
        )
        agent_user = self._get_agent()
        assert not StockItemGetterService.user_can_see(new_device.stock_item, agent_user)
        result = handle_device_change_request(
            agent_user,
            contract,
            new_device
        )
        print(result)
        orm.flush()
        assert old_device.stock_item.status == StockStatus.with_user
        assert old_device.stock_item.user == agent_user
        assert old_device.stock_item.client is None
        assert new_device.stock_item.status == StockStatus.installed
        assert new_device.stock_item.client == client
        assert new_device.stock_item.user is None

    @orm.db_session
    def test_device_repossession(self):
        contract = TestContractCreator.create_test_contract(
            'test_device_repossession_movement_1',
            npg_device=True
        )
        old_device = contract.linked_device
        user = self._get_user()
        ContractTerminationService.default_contract(
            contract,
            user
        )
        ContractTerminationService.repossess_device(
            contract,
            user,
            cancellation=True
        )
        orm.flush()
        assert old_device.stock_item.status == StockStatus.with_user
        assert old_device.stock_item.user == user
        assert old_device.stock_item.client is None

    @orm.db_session
    def test_device_undo_repossession(self):
        contract = TestContractCreator.create_test_contract('test_device_undo_repossession_movement_1', npg_device=True)
        client = contract.client
        old_device = contract.linked_device
        user = self._get_user()
        result = ContractTerminationService.default_contract(
            contract,
            user
        )
        result = ContractTerminationService.repossess_device(
            contract,
            user,
            cancellation=False
        )
        orm.flush()
        assert old_device.stock_item.status == StockStatus.with_user
        assert old_device.stock_item.user == user
        assert old_device.stock_item.client is None
        result = ContractUndoTerminationService.undo_default(contract, user, device=old_device)
        orm.flush()
        assert old_device.stock_item.status == StockStatus.installed
        assert old_device.stock_item.user is None
        assert old_device.stock_item.client == client

    @orm.db_session
    def test_device_undo_repossession_only_defaulted(self):
        contract = TestContractCreator.create_test_contract('test_device_undo_repossession_movement_2', npg_device=True)
        client = contract.client
        old_device = contract.linked_device
        user = self._get_user()
        result = ContractTerminationService.default_contract(
            contract,
            user
        )
        orm.flush()
        assert old_device.stock_item.status == StockStatus.installed
        assert old_device.stock_item.user is None
        assert old_device.stock_item.client == client
        result = ContractUndoTerminationService.undo_default(contract, user, device=old_device)
        orm.flush()
        assert old_device.stock_item.status == StockStatus.installed
        assert old_device.stock_item.user is None
        assert old_device.stock_item.client == client

    @orm.db_session
    def test_registration_movement(self):
        user = self._get_user()
        lead = user_mock.create_lead(name='Test', surname='LeadMovementRegistration')
        lead.offer = LoanOffer(
            name='LeadMovementRegistration',
            code='LeadMovementRegistration',
            family='Home',
            in_use=True,
            in_use_for_new_clients=True,
            registration_fee=1000,
            time_to_ownership_in_days=10,
            base_price_amount=1000,
            base_price_credit=1
        )
        EditLeadService.edit_lead(lead, {
            'status': LeadStatus.get_first(StatusCategory.awaiting_payment).id
        }, user)
        orm.flush()
        payment = PaymentCreationService.create_payment(
            lead.future_contract_reference, 1000, datetime.now(),
            'LeadMovementRegistration TEST'
        )
        orm.flush()
        ReconciliationService.get_answer_for_lead(lead, payment)
        device = self._new_npg_device()
        orm.flush()
        assert device.stock_item.status == StockStatus.orphaned
        assert device.stock_item.client is None
        result = ContractCreationService.create_from_lead_and_device(
            lead,
            device,
            user
        )
        orm.flush()
        assert device.stock_item.status == StockStatus.installed
        assert device.stock_item.client == lead.person.client
