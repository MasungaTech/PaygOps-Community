from datetime import datetime
from mock import patch
from core_system.users.models.user_model import User
from pony.orm import db_session
from payg_loan_system.devices.factories import DeviceAbstractFactory, DeviceFactory
from payg_loan_system.devices.model.device import Device
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.actions.add_account import handle_add_account_request
from tests.factories.factories import AbstractPaymentFactory
from payg_loan_system.payments.models.wallet import PaymentWallet
from payg_loan_system.actions.add_account import DeviceGetterService

class TestHandleAddAccount:
    @patch.object(Payment, 'get',
                  return_value=AbstractPaymentFactory.create())
    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceFactory.stub(contract=None))
    def test_device_not_registered(self, *args):
        with db_session:
              user = User.get(username="super_admin@test.com")
              res = handle_add_account_request(user, '12345jlks', 'foobar')

        assert res == [{'success': False,
                       'status': 'DEVICE_NOT_REGISTERED'}]

    @patch('payg_loan_system.actions.add_account.create_payment_wallet_owner',
           return_value=None)
    @patch('payg_loan_system.actions.add_account.create_mentor_request',
           return_value=None)
    @patch.object(Payment, 'get',
                  return_value=AbstractPaymentFactory.create())
    @patch.object(Device, 'get', return_value=DeviceAbstractFactory.create())
    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceAbstractFactory.create())
    def test_payment_returns_list_of_answers(self, *args):
       with db_session:
              user = User.get(username="super_admin@test.com")
              res = handle_add_account_request(user, '12345jlks', 'foobar')

              mentor_req = args[3]
              mentor_req.assert_called_once()

              assert len(res) == 2

              assert 'ACCOUNT_ALREADY_LINKED' in str(res)
              assert 'ACCOUNT_LINKING_SUCCESS' in str(res)

    @patch('payg_loan_system.actions.add_account.create_mentor_request',
           return_value=None)
    @patch.object(Payment, 'get',
                  return_value=None)
    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceAbstractFactory.create())
    def test_invalid_payment_reference(self, *args):
        with db_session:
              user = User.get(username="super_admin@test.com")
              res = handle_add_account_request(user, '12345jksc', 'foobar')

              assert res == [{'success': False,
                            'status': 'INVALID_PAYMENT_REFERENCE'}]

