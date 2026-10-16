from mock import patch, MagicMock
from shared.helpers.authorizer import authorizer


class TestAuthorizer:

    def foo(self):
        return 'Hello'

    @patch('flask_login.utils._get_user')
    def test_auth_can_access(self, current_user):
        user = MagicMock()
        user.can_access.return_value = True
        current_user.return_value = user

        a = authorizer('')
        res = a.can_access(self.foo)

        assert res == self.foo()
