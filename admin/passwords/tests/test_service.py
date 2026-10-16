from mock import Mock, patch

from admin.passwords.services.password_reset_services import PasswordResetService
from admin.passwords.services.user_login_services import UserLoginService
from core_system.users.models.user_model import User


class MockRequest:
    def __init__(self, form_val):
        self.form = form_val


def test_valid_user_gotten_by_username():
    request = MockRequest(form_val=dict(username="admin@test.com", password="test1234"))
    user_login = UserLoginService(request)

    user = user_login.user
    password = user_login.valid_password()
    assert isinstance(user, User)
    assert password


def test_invalid_user_with_no_username():
    request = MockRequest(form_val=dict(username="gibberish", password="test1234"))

    user_login = UserLoginService(request)
    user = user_login.user
    password = user_login.valid_password()
    assert not user
    assert not password


@patch('admin.passwords.services.password_reset_services.EmailSender')
@patch(
    'admin.passwords.services.password_reset_services.PasswordGenerator.generate_password',
    return_value='temporary-password'
)
def test_password_reset_email_includes_username(generate_password, email_sender):
    user = Mock(
        username='test-user',
        email='shared@example.com',
        full_name='Test User'
    )

    PasswordResetService._reset_password_and_send_email_or_sms(user, 'email')

    email_body = email_sender.call_args[0][3]
    assert 'Your username is: <i>test-user</i>' in email_body
    assert 'Your new password is: <i>temporary-password</i>' in email_body
    generate_password.assert_called_once_with()
    email_sender.return_value.send.assert_called_once_with()


@patch('admin.passwords.services.password_reset_services.SMSSend.SendMessage')
@patch(
    'admin.passwords.services.password_reset_services.PasswordGenerator.generate_password',
    return_value='temporary-password'
)
def test_password_reset_sms_includes_username(generate_password, send_message):
    person = Mock()
    person.preferred_phone_number.return_value = '+123456789'
    user = Mock(username='test-user', person=person)

    PasswordResetService._reset_password_and_send_email_or_sms(user, 'sms')

    sms_body = send_message.call_args[0][1]
    assert 'Your username is: test-user' in sms_body
    assert 'Your new password is temporary-password' in sms_body
    generate_password.assert_called_once_with()
