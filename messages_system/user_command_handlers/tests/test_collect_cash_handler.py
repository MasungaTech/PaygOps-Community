from mock import patch
from core_system.users.models.user_model import User
import pytest
from pony.orm import db_session
from tests.factories.factories import AbstractUserFactory
from payg_loan_system.devices.factories import DeviceAbstractFactory
from messages_system.user_command_handlers.collect_cash_handler import CollectCashSMSCommandService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService


class TestCollectCashHandler:

    @pytest.mark.parametrize("command", [
        "FOO_CODE*1000*ANOTHER",
        "FOO_CODE**",
        "FOO_CODE"
    ])
    @db_session
    def test_invalid_command_format(self,super_admin_user, command):
        result = CollectCashSMSCommandService.process(this_user=super_admin_user(),
                                                      from_number='',
                                                      variables=command)

        assert result == {'success': False,
                          'status': 'INVALID_USER_COMMAND',
                          'proper_command_syntax': 'PAYCASH# DeviceCode * Amount'}

    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceAbstractFactory.create())
    def test_invalid_amount(self, super_admin_user, *args):
        with db_session:
            result = CollectCashSMSCommandService.process(this_user=super_admin_user(),
                                                        from_number='',
                                                        variables='FOO_CODE*23,900')

        assert result == {'success': False,
                          'status': 'INVALID_NUMBER_FORMAT'}

    @patch('messages_system.user_command_handlers.collect_cash_handler.handle_paycash_request', return_value=None)
    @patch.object(DeviceGetterService, 'get_device_from_registration_code', return_value=DeviceAbstractFactory.create())
    @db_session
    def test_valid_command(self, *args):
        user = User.get(username="super_admin@test.com")
        CollectCashSMSCommandService.process(this_user=user,
                                             from_number='',
                                             variables='FOO_CODE*10000')

        device = args[0].return_value
        args[1].assert_called_with(user, 10000, this_device=device, commission=0,
                                   registration_request_code='FOO_CODE')
