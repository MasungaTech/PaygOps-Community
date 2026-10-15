from mock import patch
from core_system.users.models.user_model import User
import pytest
from pony.orm import db_session
from sales_system.leads.tests.factories import AbstractLeadFactory
from payg_loan_system.devices.factories import DeviceAbstractFactory
from messages_system.user_command_handlers.register_handler import RegisterSMSCommandService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from sales_system.leads.models.lead import Lead


class TestRegisterHandler:

    @pytest.mark.parametrize("command", [
        "FOO_CODE*LEAD_REF*ANOTHER",
        "FOO_CODE**",
        "FOO_CODE"
    ])
    def test_invalid_command_format(self, command):
        with db_session:
            result = RegisterSMSCommandService.process(this_user=User.get(username="super_admin@test.com"),
                                                    from_number='',
                                                    variables=command)

        assert result == {'success': False,
                          'status': 'INVALID_USER_COMMAND',
                          'proper_command_syntax': 'REGISTER# DeviceCode * LeadReference'}

    @patch.object(Lead, 'get', return_value=None)
    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceAbstractFactory.create())
    def test_lead_reference_invalid(self, *args):
        with db_session:
            result = RegisterSMSCommandService.process(this_user= User.get(username="super_admin@test.com"),
                                                    from_number='',
                                                    variables='DEVICE_CODE*LEAD_REFERENCE')

        assert result == {'success': False,
                          'status': 'LEAD_REFERENCE_INVALID'}

    @patch('messages_system.user_command_handlers.register_handler.register_lead', return_value=None)
    @patch.object(Lead, 'get', return_value=AbstractLeadFactory.create_no_client())
    @patch.object(DeviceGetterService, 'get_device_from_registration_code', return_value=DeviceAbstractFactory.create())
    def test_valid_command(self,  *args):
        with db_session:
            user = User.get(username="super_admin@test.com")

        RegisterSMSCommandService.process(this_user=user,
                                          from_number='',
                                          variables='DEVICE_CODE*LEAD_REFERENCE')

        args[2].assert_called_with(user,
                                   args[1].return_value,
                                   args[0].return_value,
                                   'DEVICE_CODE')
