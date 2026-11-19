from core_system.users.models.user_model import User
from mock import patch
from pony.orm import db_session
from payg_loan_system.contracts.services.contract_undo_termination_service import ContractUndoTerminationService, ContractStatus
from payg_loan_system.contracts.services.tests.factories import ContractFactory, DeviceFactory
from payg_loan_system.offers.tests.factories import TimeOfferFactory
from shared.services.settings_service import SettingsService
from tests.support.mock_query import MockQuery
from datetime import datetime


def _stub_contract(**kwargs):
    contract = ContractFactory.stub(**kwargs)
    contract.client.contracts = MockQuery([])
    return contract


class TestContractUndoTerminationService:

    @db_session
    def test_undo_default_contract_without_device_no_device(self):
        contract = _stub_contract()
        contract.linked_device = None
        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
        approver = User.get(username="super_admin@test.com")

        result = ContractUndoTerminationService.undo_default(contract, approver)

        assert result == {'success': False, 'status': 'CONTRACT_HAS_NO_DEVICE'}

    @patch('payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._create_contract_event_object')
    @patch('payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._send_data_to_hook_undo_default')
    @patch('payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._update_contract_cache')
    @db_session
    def test_undo_default_without_device_when_offer_is_not_linked_to_product(self, *_):
        contract = _stub_contract()
        contract.linked_device = None
        contract.offer.linked_to_product = False
        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
        approver = User.get(username="super_admin@test.com")

        result = ContractUndoTerminationService.undo_default(contract, approver)

        assert result == {'success': True}
        assert contract.status == ContractStatus.active

    @patch('payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._create_contract_event_object')
    @patch('payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._send_data_to_hook_undo_default')
    @patch('payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._update_contract_cache')
    @db_session
    def test_undo_default_without_device_when_platform_allows_optional_devices(self, *_):
        contract = _stub_contract()
        contract.linked_device = None
        contract.offer.linked_to_product = True
        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
        approver = User.get(username="super_admin@test.com")
        original = SettingsService.get_setting

        def get_setting(key, include_obsolete=False, setting=None):
            if key == 'ContractDeviceRestrictions':
                return 'both'
            return original(key, include_obsolete=include_obsolete, setting=setting)

        with patch.object(SettingsService, 'get_setting', side_effect=get_setting):
            result = ContractUndoTerminationService.undo_default(contract, approver)

        assert result == {'success': True}
        assert contract.status == ContractStatus.active

    @db_session
    def test_undo_default_contract_without_device_not_defaulted(self):
        contract = _stub_contract()
        contract.status = ContractStatus.active
        approver = User.get(username="super_admin@test.com")

        result = ContractUndoTerminationService.undo_default(contract, approver)

        assert result == {'success': False, 'status': 'CONTRACT_NOT_DEFAULTED'}

    @patch('payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._create_contract_event_object')
    @patch('payg_loan_system.contracts.services.contract_undo_termination_service.ContractUndoTerminationService._update_contract_cache')
    @db_session
    def test_undo_default_contract_without_device_success(self, mock_update_cache, mock_create_event):
        contract = _stub_contract()
        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
        approver = User.get(username="super_admin@test.com")
        result = ContractUndoTerminationService.undo_default(contract, approver)

        assert result == {'success': True}
        assert contract.end_time == None
        assert contract.repossession_time == None

    @db_session
    def test_undo_default_contract_with_device_already_device(self):
        contract = _stub_contract()
        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
        approver = User.get(username="super_admin@test.com")
        device = DeviceFactory.stub()

        result = ContractUndoTerminationService.undo_default(contract, approver, device)

        assert result == {'success': False, 'status': 'CONTRACT_HAS_OTHER_DEVICE'}

    @db_session
    def test_undo_default_contract_with_device_already_registered(self):
        contract = _stub_contract()
        contract.linked_device = None
        contract.offer = TimeOfferFactory.stub()
        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
        approver = User.get(username="super_admin@test.com")
        device = DeviceFactory.stub()
        device.contract = ContractFactory.stub()

        result = ContractUndoTerminationService.undo_default(contract, approver, device)

        assert result == {'success': False, 'status': 'DEVICE_ALREADY_REGISTERED', 'device_owner_id': device.contract.client.id}

    @db_session
    def test_undo_default_contract_with_device_not_allowed_offer(self):
        contract = _stub_contract()
        contract.linked_device = None
        contract.offer = TimeOfferFactory.stub(device_type='XXX')
        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
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
    @db_session
    def test_undo_default_contract_with_device_success(
            self, mock_update_cache, mock_send_hook, mock_create_event):
        contract = _stub_contract()
        contract.linked_device = None
        contract.status = ContractStatus.defaulted
        contract.end_time = datetime.now()
        contract.repossession_time = datetime.now()
        approver = User.get(username="super_admin@test.com")
        device = DeviceFactory.stub()
        device.contract = None

        result = ContractUndoTerminationService.undo_default(contract, approver, device)

        assert result == {'success': True}
        assert contract.end_time == None
        assert contract.repossession_time == None
        assert contract.client.termination_date == None
