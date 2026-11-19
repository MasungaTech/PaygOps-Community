from decimal import Decimal

import pytest
from jsonschema import validate
from mock import patch

from core_system.users.models.user_model import User
from core_system.users.services.edit_user_service import EditUserService


class _CashLimitUserStub:
    cash_limit_overall = User.cash_limit_overall
    cash_allowance = User.cash_allowance

    def __init__(self, cash_collection_limit=None, total_cash_collected=Decimal(0), total_reconciled=Decimal(0)):
        self.cash_collection_limit = cash_collection_limit
        self.total_cash_collected = total_cash_collected
        self.total_reconciled = total_reconciled


def _settings(enabled=True, platform_limit=None):
    values = {'CashCollectionLimitEnabled': enabled, 'CashCollectionLimit': platform_limit}
    return patch('core_system.users.models.user_model.SettingsService.get_setting', side_effect=values.get)


class TestCashCollectionLimitSchema:

    @pytest.mark.parametrize('value', [None, '', 0, 30000, '0', '30000.5'])
    def test_edit_schema_accepts_empty_or_numeric_limit(self, value):
        schema = User.get_model_schema(op='edit', for_validate=True)
        validate({'cash_collection_limit': value}, schema)


class TestGetCashLimitFromData:

    @pytest.mark.parametrize('value', [0, '0', '0.00', Decimal(0)])
    def test_zero_is_kept_as_a_limit(self, value):
        assert EditUserService._get_cash_limit_from_data({'cash_collection_limit': value}) == value

    @pytest.mark.parametrize('value', [None, '', '  '])
    def test_empty_means_platform_default(self, value):
        assert EditUserService._get_cash_limit_from_data({'cash_collection_limit': value}) is None

    def test_missing_key_keeps_existing_user_limit(self):
        user = _CashLimitUserStub(cash_collection_limit=Decimal(0))
        assert EditUserService._get_cash_limit_from_data({}, user) == Decimal(0)

    def test_empty_value_clears_existing_user_limit(self):
        user = _CashLimitUserStub(cash_collection_limit=Decimal(500))
        assert EditUserService._get_cash_limit_from_data({'cash_collection_limit': ''}, user) is None


class TestCashLimitOverall:

    def test_user_limit_of_zero_overrides_platform_default(self):
        with _settings(platform_limit=Decimal(1000)):
            assert _CashLimitUserStub(cash_collection_limit=Decimal(0)).cash_limit_overall == Decimal(0)

    def test_empty_user_limit_uses_platform_default(self):
        with _settings(platform_limit=Decimal(1000)):
            assert _CashLimitUserStub().cash_limit_overall == Decimal(1000)

    def test_empty_platform_default_is_unlimited(self):
        with _settings(platform_limit=None):
            assert _CashLimitUserStub().cash_limit_overall is None

    def test_platform_default_of_zero_is_a_limit(self):
        with _settings(platform_limit=Decimal(0)):
            assert _CashLimitUserStub().cash_limit_overall == Decimal(0)

    def test_disabled_on_platform(self):
        with _settings(enabled=False, platform_limit=Decimal(1000)):
            assert _CashLimitUserStub(cash_collection_limit=Decimal(0)).cash_limit_overall is None


class TestCashAllowance:

    def test_user_limit_of_zero_gives_no_allowance(self):
        with _settings(platform_limit=Decimal(1000)):
            assert _CashLimitUserStub(cash_collection_limit=Decimal(0)).cash_allowance == Decimal(0)

    def test_user_limit_of_zero_allowance_comes_from_prepayments(self):
        user = _CashLimitUserStub(cash_collection_limit=Decimal(0), total_cash_collected=Decimal(200),
                                  total_reconciled=Decimal(500))
        with _settings():
            assert user.cash_allowance == Decimal(300)

    def test_empty_platform_default_is_unlimited(self):
        with _settings(platform_limit=None):
            assert _CashLimitUserStub(total_cash_collected=Decimal(200)).cash_allowance is None
