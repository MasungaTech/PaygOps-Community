from shared.helpers.client_creator import ClientCreator
from core_system.users.models.user_model import User
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from mock import patch
import pytest
from pony.orm import db_session
from payg_loan_system.contracts.services.contract_undo_termination_service import ContractUndoTerminationService, ContractStatus
from payg_loan_system.contracts.services.tests.factories import ContractFactory, DeviceFactory
from tests.factories.factories import AbstractUserFactory
from payg_loan_system.offers.tests.factories import TimeOfferFactory
from datetime import datetime


class TestContractUndoTerminationService:

    @pytest.fixture(autouse=True)
    def test_undo_default_contract_without_device_no_device(self, api_client, good_api_key, *args):
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        contract.linked_device = None
        contract.status = ContractStatus.defaulted
        approver = User.get(username="super_admin@test.com")
        contract.client.__class__.first_active_contract = False
        contract.client.__class__.first_active_or_late_contract = False

        result = ContractUndoTerminationService.undo_default(contract, approver)

        assert result == {'success': False, 'status': 'CONTRACT_HAS_NO_DEVICE'}

    @pytest.fixture(autouse=True)
    def test_undo_default_contract_without_device_not_defaulted(self, api_client, good_api_key, *args):
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        contract.status = ContractStatus.active
        approver = User.get(username="super_admin@test.com")

        result = ContractUndoTerminationService.undo_default(contract, approver)

        assert result == {'success': False, 'status': 'CONTRACT_NOT_DEFAULTED'}

    @patch('payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._create_contract_event_object')
    @db_session
    @pytest.fixture(autouse=True)
    def test_undo_default_contract_without_device_success(self, api_client, good_api_key, *args):
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        contract.offer = TimeOfferFactory.stub()
        contract.status = ContractStatus.defaulted
        contract.end_time  = datetime.now()
        approver = User.get(username="super_admin@test.com")
        result = ContractUndoTerminationService.undo_default(contract, approver)

        assert result == {'success': True}
        assert contract.end_time == None
        assert contract.repossession_time == None

    @pytest.fixture(autouse=True)
    def test_undo_default_contract_with_device_already_device(self, api_client, good_api_key, *args):
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        contract.linked_device = DeviceFactory.stub()
        contract.status = ContractStatus.defaulted
        approver = User.get(username="super_admin@test.com")
        device = DeviceFactory.stub()

        result = ContractUndoTerminationService.undo_default(contract, approver, device)

        assert result == {'success': False, 'status': 'CONTRACT_HAS_OTHER_DEVICE'}

    @pytest.fixture(autouse=True)
    def test_undo_default_contract_with_device_already_registered(self, api_client, good_api_key, *args):
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        contract.linked_device = None
        contract.offer = TimeOfferFactory.stub()
        contract.status = ContractStatus.defaulted
        approver = User.get(username="super_admin@test.com")
        device = DeviceFactory.stub()
        device.contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()

        result = ContractUndoTerminationService.undo_default(contract, approver, device)

        assert result == {'success': False, 'status': 'DEVICE_ALREADY_REGISTERED', 'device_owner_id': device.contract.client.id}

    @pytest.fixture(autouse=True)
    def test_undo_default_contract_with_device_not_allowed_offer(self, api_client, good_api_key, *args):
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        contract.linked_device = None
        contract.offer = TimeOfferFactory.stub(device_type='XXX')
        contract.status = ContractStatus.defaulted
        approver = User.get(username="super_admin@test.com")
        device = DeviceFactory.stub(type='AAA')
        device.contract = None

        result = ContractUndoTerminationService.undo_default(contract, approver, device)

        assert result == {'success': False, 'status': 'DEVICE_NOT_ALLOWED_ON_OFFER'}

    @patch(
        'payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._create_contract_event_object')
    @patch(
        'payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._send_data_to_hook_undo_default')
    @patch(
        'payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._update_contract_cache')
    @pytest.fixture(autouse=True)
    def test_undo_default_contract_with_device_success(self, api_client, good_api_key, *args):
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        contract.linked_device = None
        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
        contract.repossession_time = datetime.now()
        approver = User.get(username="super_admin@test.com") #AbstractUserFactory.create()
        device = DeviceCreateService.create("SFSFGG333", "NPG", 1) # DeviceFactory.stub()
        device.contract = None

        result = ContractUndoTerminationService.undo_default(contract, approver, device)

        assert result == {'success': True}
        assert contract.end_time == None
        assert contract.repossession_time == None
        assert contract.client.termination_date == None


