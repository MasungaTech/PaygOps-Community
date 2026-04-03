from datetime import datetime
from tests.support.mock_query import MockQuery
from payg_loan_system.contracts.models.reconciled_payment_model import ReconciledPayment
import mock
from pony.orm import db_session
from payg_loan_system.contracts.services.contract_change_service import ContractChangeService
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.contracts.services.tests.factories import ContractFactory
from payg_loan_system.offers.tests.factories import TimeOfferFactory
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator


class TestContractChangeService:

    @db_session
    def test_offer_does_not_exist(self, *args):
        user = User.get(username="view_only@test.com")
        contract = ContractFactory.stub()
        new_offer = None

        result = ContractChangeService.change_contract_offer(contract, new_offer, user)

        assert result == {'success': False, 'status': 'OFFER_DOES_NOT_EXIST'}

    @db_session
    def test_offer_disabled(self, super_admin_user, *args):
        user = super_admin_user()
        contract = ContractFactory.stub()
        new_offer = TimeOfferFactory.stub(code='2', in_use=False)

        result = ContractChangeService.change_contract_offer(contract, new_offer, user)

        assert result == {'success': False, 'status': 'OFFER_DISABLED'}

    @db_session
    def test_device_cannot_use_offer(self, super_admin_user,*args):
        user = super_admin_user()
        contract = ContractFactory.stub()
        new_offer = TimeOfferFactory.stub(code='3', device_type='XXX')
        new_offer.in_use_for_new_clients = True

        result = ContractChangeService.change_contract_offer(contract, new_offer, user)

        assert result == {'success': False, 'status': 'DEVICE_NOT_ALLOWED_ON_OFFER'}

    @db_session
    def test_offer_change_impossible_value_below_deposit(self, super_admin_user, *args):
        user = super_admin_user()
        contract = ContractFactory.stub()
        contract.get_cumulative_amount_repaid = mock.Mock(return_value=1000)
        new_offer = TimeOfferFactory.stub(code='4', registration_fee=2000)
        new_offer.in_use_for_new_clients = True

        result = ContractChangeService.change_contract_offer(contract, new_offer, user)

        assert result == {'success': False, 'status': 'OFFER_CHANGE_FAILED_AMOUNT_PAID_BELOW_DEPOSIT'}

    @db_session
    def test_offer_change_database(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key, offer_data={"code": "OLD_OFFER_CHANGE_OFFER"})
        contract = client.contracts.select().first()
        user = User.get(username="super_admin@test.com")
        before = datetime.now()

        assert contract.offer_at(before).code == 'OLD_OFFER_CHANGE_OFFER'
        assert contract.offer_at().code == 'OLD_OFFER_CHANGE_OFFER'

        offer_data = ClientCreator.offer_data
        offer_data.update({"code": "NEW_OFFER_CHANGE_OFFER"}) 
        new_offer = CreateOfferService.add_from_data_and_user(offer_data, user)
        ContractChangeService.change_contract_offer(contract, new_offer, user)
        after = datetime.now()

        assert contract.offer_at(before).code == 'OLD_OFFER_CHANGE_OFFER'
        assert contract.offer_at(after).code == 'NEW_OFFER_CHANGE_OFFER'
        assert contract.offer_at().code == 'NEW_OFFER_CHANGE_OFFER'

        offer_data.update({"code": "LAST_OFFER_CHANGE_OFFER"})
        new_offer = CreateOfferService.add_from_data_and_user(offer_data, user)
        ContractChangeService.change_contract_offer(contract, new_offer, user)
        after_all = datetime.now()

        assert contract.offer_at(before).code == 'OLD_OFFER_CHANGE_OFFER'
        assert contract.offer_at(after).code == 'NEW_OFFER_CHANGE_OFFER'
        assert contract.offer_at(after_all).code == 'LAST_OFFER_CHANGE_OFFER'
        assert contract.offer_at().code == 'LAST_OFFER_CHANGE_OFFER'
