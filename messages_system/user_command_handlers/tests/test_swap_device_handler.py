from mock import patch
from core_system.users.models.user_model import User
import pytest
from pony.orm import db_session
from sales_system.leads.tests.factories import AbstractLeadFactory
from payg_loan_system.devices.factories import DeviceAbstractFactory
from messages_system.user_command_handlers.swap_device_handler import SwapDeviceSMSCommandService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from sales_system.leads.models.lead import Lead


class TestRegisterHandler:

    @pytest.mark.parametrize("command", [
        "FOO_CODE*FOO_CODE_2*ANOTHER",
        "FOO_CODE**",
        "FOO_CODE"
    ])
    def test_invalid_command_format(self, command):
        with db_session:
            result = SwapDeviceSMSCommandService.process(this_user=User.get(username="super_admin@test.com"),
                                                    from_number='',
                                                    variables=command)

        assert result == {'success': False,
                          'status': 'INVALID_USER_COMMAND',
                          'proper_command_syntax': 'CHANGEDEVICE# OldDeviceCode * NewDeviceCode'}


    @patch('messages_system.user_command_handlers.swap_device_handler.handle_device_change_request', return_value=None)
    @patch.object(DeviceGetterService, 'get_device_from_registration_code', return_value=DeviceAbstractFactory.create())
    def test_valid_command(self,  *args):
        with db_session:
            user = User.get(username="super_admin@test.com")

        result = SwapDeviceSMSCommandService.process(this_user=user,
                                                     from_number='',
                                                     variables='FOO_CODE_1*FOO_CODE_2')

        args[1].assert_called_with(user,
                                   args[0].return_value.contract,
                                   args[0].return_value,
                                   'FOO_CODE_1', 'FOO_CODE_2')
