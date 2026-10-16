from pony.orm import db_session
from core_system.role.models import Permission


class TestPermission:
    @db_session
    def test_required_permission_constant(self):
        expected_code_names = [
            'ViewClients',
            'ViewLeads'
        ]

        assert sorted(expected_code_names) == sorted(Permission.REQUIRED_CODE_NAMES)

    @db_session
    def test_list_has_at_least_one_required_permission_returns_false(self):
        assert Permission.has_one_required_permission([]) is False

    @db_session
    def test_list_has_at_least_one_required_permission_returns_true(self):
        assert Permission.has_one_required_permission(Permission.select()) is True
