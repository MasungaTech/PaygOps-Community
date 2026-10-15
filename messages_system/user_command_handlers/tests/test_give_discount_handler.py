from mock import patch
from core_system.users.models.user_model import User
import pytest
from pony.orm import db_session
from payg_loan_system.devices.factories import DeviceAbstractFactory
from messages_system.user_command_handlers.give_discount_handler import GiveDiscountSMSCommandService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService


class TestGiveDiscountHandler:

    @pytest.mark.parametrize("command", [
        "FOO_CODE*1000*ANOTHER",
        "FOO_CODE**",
        "FOO_CODE"
    ])
    def test_invalid_command_format(self, command):
        with db_session:
            result = GiveDiscountSMSCommandService.process(this_user=User.get(username="super_admin@test.com"),
                                                        from_number='',
                                                        variables=command)

        assert result == {'success': False,
                          'status': 'INVALID_USER_COMMAND',
                          'proper_command_syntax': 'GIVEDISCOUNT# DeviceCode * NumberOfDays'}

    @patch.object(DeviceGetterService, 'get_device_from_registration_code',
                  return_value=DeviceAbstractFactory.create())
    def test_invalid_amount(self, *args):
        with db_session:
            result = GiveDiscountSMSCommandService.process(this_user=User.get(username="super_admin@test.com"),
                                                        from_number='',
                                                        variables='FOO_CODE*3.2')

        assert result == {'success': False,
                          'status': 'INVALID_NUMBER_FORMAT'}

    @patch('messages_system.user_command_handlers.give_discount_handler.give_discount', return_value=None)
    @patch.object(DeviceGetterService, 'get_device_from_registration_code', return_value=DeviceAbstractFactory.create())
    def test_valid_command(self, *args):
        with db_session:
            user = User.get(username="super_admin@test.com")
        GiveDiscountSMSCommandService.process(this_user=user,
                                              from_number='',
                                              variables='FOO_CODE*2')

        device = args[0].return_value
        args[1].assert_called_with(acting_user=user,
                                   discounted_units=2,
                                   registration_request_code='FOO_CODE',
                                   this_device=device)
