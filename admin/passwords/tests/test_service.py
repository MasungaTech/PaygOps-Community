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
