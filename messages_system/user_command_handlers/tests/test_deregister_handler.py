from mock import patch
from core_system.users.models.user_model import User
import pytest
from pony.orm import db_session
from payg_loan_system.devices.factories import DeviceAbstractFactory
from messages_system.user_command_handlers.deregister_handler import DeRegisterSMSCommandService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService


class TestDeRegisterHandler:

    @pytest.mark.parametrize("command", [
        "FOO_CODE*LEAD_REF*ANOTHER",
        "FOO_CODE**",
        "FOO_CODE*ANOTHER"
    ])
    def test_invalid_command_format(self, command):
        with db_session:
            result = DeRegisterSMSCommandService.process(this_user=User.get(username="super_admin@test.com"),
                                                        from_number='',
                                                        variables=command)

        assert result == {'success': False,
                          'status': 'INVALID_USER_COMMAND',
                          'proper_command_syntax': 'DEREGISTER# DeviceCode'}

    @patch('messages_system.user_command_handlers.deregister_handler.handle_deregistration_request', return_value=None)
    @patch.object(DeviceGetterService, 'get_device_from_registration_code', return_value=DeviceAbstractFactory.create())
    def test_valid_command(self,  *args):
        with db_session:
            user = User.get(username="super_admin@test.com")

        DeRegisterSMSCommandService.process(this_user=user,
                                            from_number='',
                                            variables='DEVICE_CODE')

        args[1].assert_called_with(user,
                                   args[0].return_value,
                                   'DEVICE_CODE')
