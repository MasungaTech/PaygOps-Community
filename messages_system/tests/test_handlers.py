from datetime import datetime
from mock import patch
from pony.orm import db_session
import pytest
from core_system.client.services.client_getter_service import ClientGetterService

from messages_system.services import user_sms_handler
from core_system.client.models import Client
from tests.factories.factories import AbstractClientFactory, AbstractUserFactory
from payg_loan_system.devices.factories import DeviceAbstractFactory

from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService


class BaseTestHandler:
    recep_time = datetime.now()
    phone_number = '123456789'
    user = AbstractUserFactory.create()
    variables = ''

    def assert_valid_command(self, func, *args):
        resp = func(self.user,
                    self.phone_number,
                    self.variables,
                    self.recep_time)
        assert resp == 1
        args[-1][0].assert_called_with(self.user, *args[:-1])


class TestSyncSettingsHandler(BaseTestHandler):
    variables = 'FOO_CODE'

    @db_session
    @patch('messages_system.services.user_sms_handler.handle_device_sync_settings_request', return_value={
        'success': True,
        'status': 'DEVICE_SETTINGS_SYNC_SUCCESS',
        'registration_answer_code': 'EXAMPLE',
        'device_serial': 'SOL-123'})
    def test_valid_command(self, *args):
        self.assert_valid_command(user_sms_handler.syncsettings_command_handler,
                                  'FOO_CODE',
                                  args)

    @db_session
    @pytest.mark.parametrize("test_input, result", [
        ("FOO_CODE*LEAD_REF*ANOTHER", 1),
        ("FOO_CODE*", 1),
        ("FOO_CODE**", 1)
    ])
    def test_invalid_command(self, test_input, result):
        resp = user_sms_handler.syncsettings_command_handler(self.user,
                                                             self.phone_number,
                                                             test_input,
                                                             self.recep_time)
        assert resp == result


class TestChangeOfferHandler(BaseTestHandler):
    variables = 'FOO_CODE*BAR'

    @db_session
    @patch('messages_system.services.user_sms_handler.handle_offer_change_request', return_value={
        'success': True,
        'status': 'OFFER_CHANGE_SUCCESS',
        'device_serial': 'SOL-123',
        'new_offer_code': 'EX1',
        'weeks_paid': 2,
        'days_paid': 3,
        'weeks_to_pay': 52,
        'registration_answer_code': 'EXAMPLE'
    })
    def test_valid_command(self, *args):
        self.assert_valid_command(user_sms_handler.changeoffer_command_handler,
                                  'FOO_CODE',
                                  'BAR',
                                  args)

    @db_session
    @pytest.mark.parametrize("test_input, result", [
        ("FOO_CODE*LEAD_REF*ANOTHER", 1),
        ("FOO_CODE", 1),
        ("", 1),
        ("FOO_CODE**", 1)
    ])
    def test_invalid_command(self, test_input, result):
        resp = user_sms_handler.changeoffer_command_handler(self.user,
                                                            self.phone_number,
                                                            test_input,
                                                            self.recep_time)
        assert resp == result


class TestForceActivateHandler(BaseTestHandler):
    variables = 'FOO_CODE*666*999'

    @db_session
    @patch('messages_system.services.user_sms_handler.handle_direct_activation_request', return_value={
        'success': True, 'status': 'ACTIVATION_REQUEST_SUCCESS',
        'activation_answer_code': 'EXAMPLE',
        'expiration_time_day': datetime.now().strftime('%d'),
        'expiration_time_month': datetime.now().strftime('%m'),
        'expiration_time_year': datetime.now().strftime('%Y'),
    })
    def test_valid_command(self, *args):
        self.assert_valid_command(user_sms_handler.forceactivate_command_handler,
                                  '666',
                                  'FOO_CODE',
                                  999,
                                  args)

    @db_session
    @pytest.mark.parametrize("test_input, result", [
        ("FOO_CODE*LEAD_REF", 1),
        ("FOO_CODE", 1),
        ("FOO_CODE*BAR", 1),
        ("", 1),
        ("FOO_CODE**", 1)
    ])
    def test_invalid_command(self, test_input, result):
        resp = user_sms_handler.forceactivate_command_handler(self.user,
                                                              self.phone_number,
                                                              test_input,
                                                              self.recep_time)
        assert resp == result


class TestAddMpesaHandler(BaseTestHandler):
    variables = 'FOO_CODE*BAR'

    @db_session
    @patch('messages_system.services.user_sms_handler.handle_add_account_request', return_value={
        'success': True,
        'status': 'ACCOUNT_LINKING_SUCCESS',
        'account_owner_name': 'example',
        'account_owner_id': 1,
        'account_name': 'EXAMPLE'
    })
    def test_valid_command(self, *args):
        self.assert_valid_command(user_sms_handler.addmpesa_command_handler,
                                  'FOO_CODE',
                                  'BAR',
                                  args)

    @db_session
    @pytest.mark.parametrize("test_input, result", [
        ("FOO_CODE*LEAD_REF*ANOTHER", 1),
        ("FOO_CODE", 1),
        ("", 1),
        ("FOO_CODE**", 1)
    ])
    def test_invalid_command(self, test_input, result):
        resp = user_sms_handler.addmpesa_command_handler(self.user,
                                                         self.phone_number,
                                                         test_input,
                                                         self.recep_time)
        assert resp == result


class TestAddPhoneNumberHandler(BaseTestHandler):
    variables = 'FOO_CODE*BAR'

    @db_session
    @patch('messages_system.services.user_sms_handler.handle_add_phone_number_request', return_value={
        'success': True, 'status': 'ADD_PHONE_NUMBER_SUCCESS',
        'name': 'example',
        'surname': '',
        'client_id': 1,
        'phone_number': '+111222333444'
    })
    def test_valid_command(self, *args):
        self.assert_valid_command(user_sms_handler.addphonenumber_command_handler,
                                  'FOO_CODE',
                                  'BAR',
                                  args)

    @db_session
    @pytest.mark.parametrize("test_input, result", [
        ("FOO_CODE*LEAD_REF*ANOTHER", 1),
        ("FOO_CODE", 1),
        ("", 1),
        ("FOO_CODE**", 1)
    ])
    def test_invalid_command(self, test_input, result):
        resp = user_sms_handler.addphonenumber_command_handler(self.user,
                                                               self.phone_number,
                                                               test_input,
                                                               self.recep_time)
        assert resp == result


class TestUnlockHandler(BaseTestHandler):
    variables = 'FOO_CODE*3'

    @db_session
    @patch.object(ClientGetterService, 'get_from_user_and_id', return_value=AbstractClientFactory.create())
    @patch('messages_system.services.user_sms_handler.handle_unlock_request', return_value={
        'success': True,
        'status': 'UNLOCK_SUCCESS',
        'unlock_code': 'Example'
    })
    def test_valid_command(self, *args):
        self.assert_valid_command(user_sms_handler.unlock_command_handler,
                                  args[1].return_value,
                                  'FOO_CODE',
                                  args)

    @db_session
    @pytest.mark.parametrize("test_input, result", [
        ("FOO_CODE*LEAD_REF*ANOTHER", 1),
        ("FOO_CODE", 1),
        ("FOO_CODE*BAR", 1),
        ("", 1),
        ("FOO_CODE**", 1)
    ])
    def test_invalid_command(self, test_input, result):
        resp = user_sms_handler.unlock_command_handler(self.user,
                                                       self.phone_number,
                                                       test_input,
                                                       self.recep_time)
        assert resp == result


class TestGetCodeHandler(BaseTestHandler):

    @db_session
    @patch.object(ClientGetterService, 'get_from_user_and_id', return_value=AbstractClientFactory.create())
    @patch('messages_system.services.user_sms_handler.handle_activation_request',
           return_value={
                'success': True,
                'status': 'ACTIVATION_REQUEST_SUCCESS',
                'activation_answer_code': 'FOOOOO',
                'expiration_time_day': datetime.now().strftime('%d'),
                'expiration_time_month': datetime.now().strftime('%m'),
                'expiration_time_year': datetime.now().strftime('%Y'),
           })
    def test_valid_two_part_command(self, *args):
        variables = 'FOO_CODE*123'

        resp = user_sms_handler.getcode_command_handler(self.user,
                                                        self.phone_number,
                                                        variables,
                                                        self.recep_time)
        args[0].assert_called_with(args[1].return_value,
                                   'FOO_CODE')

        assert resp == 1

    @db_session
    @patch('messages_system.services.user_sms_handler.handle_activation_request',
           return_value={
                'success': True,
                'status': 'ACTIVATION_REQUEST_SUCCESS',
                'activation_answer_code': 'FOOOOO',
                'expiration_time_day': datetime.now().strftime('%d'),
                'expiration_time_month': datetime.now().strftime('%m'),
                'expiration_time_year': datetime.now().strftime('%Y'),
           })
    @patch.object(Client, 'get', return_value=AbstractClientFactory.create())
    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceAbstractFactory.create())
    def test_valid_one_part_command(self, device_mock, client_mock, activation_mock):
        variables = 'FOO_CODE'

        resp = user_sms_handler.getcode_command_handler(self.user,
                                                        self.phone_number,
                                                        variables,
                                                        self.recep_time)
        device_mock.assert_called_with(variables)
        activation_mock.assert_called_with(
            device_mock.return_value.contract.client, variables)

        assert resp == 1

    @db_session
    @pytest.mark.parametrize("test_input, result", [
        ("FOO_CODE*LEAD_REF*ANOTHER", 1),
        ("FOO_CODE", 1),
        ("FOO_CODE**", 1)
    ])
    def test_invalid_command(self, test_input, result):
        resp = user_sms_handler.getcode_command_handler(self.user,
                                                        self.phone_number,
                                                        test_input,
                                                        self.recep_time)
        assert resp == result
