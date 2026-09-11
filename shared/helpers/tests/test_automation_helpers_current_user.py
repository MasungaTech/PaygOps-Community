from types import SimpleNamespace

from shared.helpers.automation_helpers import (
    resolve_automation_current_user,
    _is_usable_user,
)


class _UserLike:
    """Mirrors PaygOps User: is_anonymous is a method, not a bool attribute."""

    def __init__(self, id, active=True, anonymous=False):
        self.id = id
        self.active = active
        self._anonymous = anonymous

    def is_anonymous(self):
        return self._anonymous


def test_is_usable_user_rejects_none_and_inactive():
    assert _is_usable_user(None) is False
    assert _is_usable_user(_UserLike(id=-1)) is False
    assert _is_usable_user(_UserLike(id=0)) is False
    assert _is_usable_user(_UserLike(id=5, active=False)) is False
    assert _is_usable_user(_UserLike(id=5, anonymous=True)) is False
    assert _is_usable_user(_UserLike(id=5)) is True


def test_is_usable_user_handles_bool_is_anonymous_attribute():
    assert _is_usable_user(SimpleNamespace(id=5, active=True, is_anonymous=True)) is False
    assert _is_usable_user(SimpleNamespace(id=5, active=True, is_anonymous=False)) is True


def test_resolve_returns_logged_in_user():
    caller = _UserLike(id=7)
    assert resolve_automation_current_user(user=caller) is caller


def test_resolve_returns_none_when_not_logged_in():
    assert resolve_automation_current_user(user=None) is None
    assert resolve_automation_current_user(user=_UserLike(id=5, anonymous=True)) is None
