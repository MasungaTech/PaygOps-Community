from datetime import datetime
from mock import patch
import pytest
from pony.orm import db_session
from tests.factories.factories import AbstractUserFactory
from messages_system.services.user_sms_handler import handle_user_SMS
from core_system.users.models.user_model import User


class BaseTestUserSmsHandler:
    RECEPTION_TIME = datetime.now()


class BaseTestUserCommandRouter(BaseTestUserSmsHandler):
    patch_fn = None
    command = None
    phone_number = '123456789'

    @patch.object(User, 'can_access', return_value=True)
    @db_session
    def exec(self, *args):
        user = User.get(username="super_admin@test.com")

        response = handle_user_SMS(user, self.phone_number, self.command, self.RECEPTION_TIME)
        return response, args

    def assert_fn_call(self, *args):
        resp, args = self.exec(args)
        assert args[0][0].call_count == 1


@patch.object(User, 'can_access', return_value=True)
class TestHandleAuthorizedUserSms(BaseTestUserSmsHandler):

    @db_session
    def test_handle_invalid_body(self, *args):

        user = User.get(username="super_admin@test.com")
        command = 'REGISTER#FOO#BAR'

        response = handle_user_SMS(user, '1234', command, self.RECEPTION_TIME)
        assert response == 1


class TestHandleUnlockCommand(BaseTestUserCommandRouter):
    command = 'UNLOCK#FOO'

    @patch('messages_system.services.user_sms_handler.unlock_command_handler')
    def test_command(self, *args):
        super().assert_fn_call(*args)


class TestGetCodeCommand(BaseTestUserCommandRouter):
    command = 'GETCODE#FOO'

    @patch('messages_system.services.user_sms_handler.getcode_command_handler')
    def test_command(self, *args):
        super().assert_fn_call(*args)


class TestAddMpesaCommand(BaseTestUserCommandRouter):
    command = 'ADDMPESA#FOO'

    @patch('messages_system.services.user_sms_handler.addmpesa_command_handler')
    def test_command(self, *args):
        super().assert_fn_call(*args)


class TestAddPhoneNumberCommand(BaseTestUserCommandRouter):
    command = 'ADDPHONENUMBER#FOO'

    @patch('messages_system.services.user_sms_handler.addphonenumber_command_handler')
    def test_command(self, *args):
        super().assert_fn_call(*args)


class TestForceActivateCommand(BaseTestUserCommandRouter):
    command = 'FORCEACTIVATE#FOO'

    @patch('messages_system.services.user_sms_handler.forceactivate_command_handler')
    def test_command(self, *args):
        super().assert_fn_call(*args)


class TestChangeOfferCommand(BaseTestUserCommandRouter):
    command = 'CHANGEOFFER#FOO'

    @patch('messages_system.services.user_sms_handler.changeoffer_command_handler')
    def test_command(self, *args):
        super().assert_fn_call(*args)


class TestSyncSettingsCommand(BaseTestUserCommandRouter):
    command = 'SYNCSETTINGS#FOO'

    @patch('messages_system.services.user_sms_handler.syncsettings_command_handler')
    def test_command(self, *args):
        super().assert_fn_call(*args)


class TestDebitCommand(BaseTestUserCommandRouter):
    command = 'DEBIT#FOO'

    @pytest.mark.skip
    @patch('messages_system.services.user_sms_handler.debit_command_handler')
    def test_command(self, *args):
        super().assert_fn_call(*args)


class TestCommandNonExistent(BaseTestUserCommandRouter):
    command = 'NOTEXISTENT#FOO'

    @db_session
    def test_command(self, *args):
        resp, args = self.exec()

        assert resp == 1
