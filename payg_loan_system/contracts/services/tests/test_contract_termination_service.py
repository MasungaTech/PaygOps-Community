from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator
from shared.helpers.assert_datetime import assert_datetime
from mock import patch
from pony.orm import db_session
from payg_loan_system.contracts.services.contract_termination_service import ContractTerminationService, ContractStatus
from payg_loan_system.contracts.services.tests.factories import ContractFactory, DeviceFactory
from tests.factories.factories import AbstractUserFactory
from datetime import datetime


class TestContractTerminationService:

    @db_session
    def test_default_contract_already_defaulted(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.defaulted
        approver = User.get(username="super_admin@test.com")

        result = ContractTerminationService.default_contract(contract, approver)

        assert result == {'success': False, 'status': 'CONTRACT_ALREADY_DEFAULTED'}

    @db_session
    def test_default_contract_already_completed(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.completed
        approver = User.get(username="super_admin@test.com")

        result = ContractTerminationService.default_contract(contract, approver)

        assert result == {'success': False, 'status': 'CONTRACT_ALREADY_COMPLETED'}

    @patch('payg_loan_system.contracts.services.contract_termination_service.ContractTerminationService._create_contract_event_object')
    @patch('payg_loan_system.contracts.services.contract_termination_service.ContractTerminationService._update_contract_cache')
    @db_session
    def test_default_contract_success(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.client.contracts = []
        approver = User.get(username="super_admin@test.com")

        result = ContractTerminationService.default_contract(contract, approver)

        assert result == {'success': True}
        assert contract.status == ContractStatus.defaulted

    @db_session
    def test_repossess_contract_not_already_defaulted(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.active
        contract.linked_device = DeviceFactory.stub()
        approver = User.get(username="super_admin@test.com")

        result = ContractTerminationService.repossess_device(contract, approver, cancellation=False)

        assert result == {'success': False, 'status': 'CONTRACT_NOT_DEFAULTED'}

    @db_session
    def test_repossess_contract_no_device(self, *args):
        contract = ContractFactory.stub()
        contract.status = ContractStatus.defaulted
        contract.linked_device = None
        approver = User.get(username="super_admin@test.com")

        result = ContractTerminationService.repossess_device(contract, approver, cancellation=False)

        assert result == {'success': False, 'status': 'CONTRACT_HAS_NO_DEVICE'}

    @db_session
    def test_repossess_contract_success(self, api_client, good_api_key, super_admin_user, *args):
        # contract = ContractFactory.stub()
        # contract.status = ContractStatus.defaulted
        # contract.linked_device = DeviceFactory.stub()
        # contract.client.contracts = []
        # approver = AbstractUserFactory.create()
        client = ClientCreator.create(api_client, good_api_key)
        contract = client.contracts.select().first()

        ContractTerminationService.default_contract(contract, super_admin_user())
        result = ContractTerminationService.repossess_device(contract, super_admin_user(), cancellation=False)

        assert result == {'success': True}
        assert_datetime(contract.client.termination_date, datetime.now())

    @db_session
    def test_cancel_contract_success(self, api_client, good_api_key, super_admin_user, *args):
        client = ClientCreator.create(api_client, good_api_key)
        contract = client.contracts.select().first()

        result = ContractTerminationService.cancel_contract(contract, super_admin_user())

        assert result == {'success': True}
        assert_datetime(contract.client.termination_date, datetime.now())