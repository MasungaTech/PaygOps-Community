from mock import patch
from pony.orm import db_session
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from tests.factories.factories import AbstractUserFactory
from core_system.users.models.user_model import User
from payg_loan_system.devices.factories import DeviceAbstractFactory, DeviceFactory
from payg_loan_system.actions.change_offer import handle_offer_change_request
from payg_loan_system.offers.tests.factories import TimeOfferFactory
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.contracts.services.contract_change_service import ContractChangeService
from payg_loan_system.contracts.services.tests.factories import ContractFactory


class TestChangeOffer:
    req_code = 'FOOBAR'
    offer_code = 'BAZBAZ'

    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceAbstractFactory.create())
    def test_user_without_auth(self, *args):
        user = AbstractUserFactory.create(authorized=False)
        resp = handle_offer_change_request(user, self.req_code, self.offer_code)

        assert resp == [{'success': False,
                       'status': 'INSUFFICIENT_PERMISSION',
                       'permission': 'DoChangeOfferActions'}]

    @patch.object(User, 'can_access', return_value=True)
    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceFactory.stub(contract=None))
    def test_user_device_is_not_registered(self, *args):
        with db_session:
            user = User.get(username="super_admin@test.com")

        resp = handle_offer_change_request(user, self.req_code, self.offer_code)

        assert resp == [{'success': False,
                        'status': 'DEVICE_NOT_REGISTERED'}]

    @patch.object(ContractChangeService, 'change_contract_offer', return_value={'success': True, 'repayments': []})
    @patch('payg_loan_system.actions.change_offer.store_request')
    @patch.object(ListOfferService, 'get_from_user_and_properties', return_value=None)
    @patch.object(User, 'can_access', return_value=True)
    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceAbstractFactory.create())
    @patch.object(DeviceAPIService, 'sync_device_settings',
                  return_value='PANCAKES')
    def test_offer_change_fail(self, *args):
        with patch.object(DeviceGetterService, 'get_device_from_registration_code',
                          return_value=DeviceAbstractFactory.create()) as mock_device:
            with db_session:
                user = User.get(username="super_admin@test.com")
            resp = handle_offer_change_request(user, self.req_code, self.offer_code)
        assert resp == [{'success': False,
                        'status': 'OFFER_DOES_NOT_EXIST'}]

    @patch.object(ContractChangeService, 'change_contract_offer', return_value={'success': True, 'repayments': []})
    @patch('payg_loan_system.actions.change_offer.store_request')
    @patch.object(ListOfferService, 'get_from_user_and_properties', return_value=TimeOfferFactory.stub(code='2', in_use=True))
    @patch.object(User, 'can_access', return_value=True)
    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceAbstractFactory.create())
    @patch.object(DeviceAPIService, 'sync_device_settings',
                  return_value='PANCAKES')
    @db_session
    def test_offer_change_success(self, *args):
        with patch.object(DeviceGetterService, 'get_device_from_registration_code',
                          return_value=DeviceAbstractFactory.create()) as mock_device:
            with db_session:
                user = User.get(username="super_admin@test.com")

            resp = handle_offer_change_request(user, self.req_code, self.offer_code)

        assert resp[0]['success'] == True
        assert resp[0]['status'] == 'OFFER_CHANGE_SUCCESS'
        assert resp[0]['device_serial'] == mock_device.return_value.get_display_name()
        assert resp[0]['registration_answer_code'] == 'PANCAKES'

    @patch.object(ContractChangeService, 'change_contract_offer', return_value={'success': True, 'repayments': []})
    @patch('payg_loan_system.actions.change_offer.store_request')
    @patch.object(ListOfferService, 'get_from_user_and_properties', return_value=TimeOfferFactory.stub(code='2', in_use=True))
    @patch.object(User, 'can_access', return_value=True)
    @patch.object(DeviceAPIService, 'sync_device_settings')
    @db_session
    def test_offer_change_success_without_device(self, mock_sync, *args):
        user = User.get(username="super_admin@test.com")
        contract = ContractFactory.stub()
        contract.linked_device = None

        resp = handle_offer_change_request(
            acting_user=user,
            new_offer_code=self.offer_code,
            this_contract=contract,
            this_device=None,
        )

        assert resp[0]['success'] is True
        assert resp[0]['status'] in (
            'OFFER_CHANGE_SUCCESS_NO_DEVICE',
            'OFFER_CHANGE_SUCCESS_NO_DEVICE_NO_PROGRESSION',
        )
        assert resp[0]['device_serial'] is None
        mock_sync.assert_not_called()
