from datetime import time
from decimal import Decimal
from pony.orm import db_session
from mock import patch
import pytest
from shared.services.settings_service import SettingsService
from shared.model.settings_model import Settings


class TestSettingsService():
    
    def test_settings_incorrect_type_validation_fails(self):
        with pytest.raises(TypeError):
            SettingsService._get_DB_compliant(5.6, 'mycustomTypeNorDefined')
        with pytest.raises(TypeError):
            SettingsService._get_type_compliant(5.6, 'mycustomTypeNorDefined')
    
    def test_settings_strings_correctly_parsed(self):
        assert SettingsService._get_type_compliant(True, 'boolean') == True
        assert SettingsService._get_type_compliant('True', 'boolean') == True
        assert SettingsService._get_type_compliant(1, 'boolean') == True
        assert SettingsService._get_type_compliant(5, 'integer') == 5
        assert SettingsService._get_type_compliant('5', 'integer') == 5
        with pytest.raises(Exception):
            SettingsService._get_type_compliant(5.6,'integer')
        with pytest.raises(Exception):
            SettingsService._get_type_compliant('5.6', 'integer')
        assert SettingsService._get_type_compliant('5', 'string') == '5'
        assert SettingsService._get_type_compliant(['5'], 'json') == ['5']
        assert SettingsService._get_type_compliant({'5':1}, 'json') == {'5':1}
        assert SettingsService._get_type_compliant('["5"]', 'json') == ['5']
        assert SettingsService._get_type_compliant('{"5":1}', 'json') == {'5':1}
        with pytest.raises(Exception): #minutes are required
            assert SettingsService._get_type_compliant("10", 'time') == time(10)
        assert SettingsService._get_type_compliant("10:20", 'time') == time(10,20)
        assert SettingsService._get_type_compliant("10:20:30", 'time') == time(10,20,30)
        assert SettingsService._get_type_compliant("10:20:30.1234", 'time') == time(10,20,30,1234)
        assert SettingsService._get_type_compliant("1.34534535", 'decimal') == Decimal('1.35')
        assert SettingsService._get_type_compliant(1.3000000, 'decimal') == Decimal('1.30')
        with pytest.raises(TypeError):
            SettingsService._get_type_compliant('sdfsd', 'decimal')

    
    @db_session
    def test_settings_all_default_values_validates_and_deletes_obsolete(self):
        Settings(key="MyTestSettingToDelete", value="DeleteThis")
        with patch.object(SettingsService, '_execute_callback'):
            SettingsService.set_defaults(override=True)
        assert Settings.get(key="MyTestSettingToDelete") == None


class TestNullableSettings:

    @pytest.fixture(autouse=True)
    def restore_cash_collection_limit(self):
        with db_session:
            previous = SettingsService.get_setting('CashCollectionLimit')
        yield
        with db_session:
            SettingsService.set_setting('CashCollectionLimit', previous)

    @pytest.mark.parametrize('empty_value', [None, ''])
    @db_session
    def test_empty_value_is_stored_as_none(self, empty_value):
        SettingsService.set_setting('CashCollectionLimit', empty_value)
        assert Settings.get(key='CashCollectionLimit').value == ''
        assert SettingsService.get_setting('CashCollectionLimit') is None

    @db_session
    def test_zero_is_kept_as_a_value(self):
        SettingsService.set_setting('CashCollectionLimit', 0)
        assert SettingsService.get_setting('CashCollectionLimit') == Decimal(0)

    @db_session
    def test_validation_still_applies_to_values(self):
        with pytest.raises(Exception):
            SettingsService.set_setting('CashCollectionPercentageWarning', 101)

    @db_session
    def test_non_nullable_setting_rejects_empty_value(self):
        with pytest.raises(TypeError):
            SettingsService.set_setting('MaxRoundingDiscount', '')


MISSING = object()


def patch_offline_mobile_app_settings(platform_type, offline_mobile_app):
    feature_toggles = {'SalesFeatures': True}
    if offline_mobile_app is not MISSING:
        feature_toggles['OfflineMobileApp'] = offline_mobile_app
    settings = {'PlatformType': platform_type, 'FeatureToggles': feature_toggles}
    return patch.object(SettingsService, 'get_setting', side_effect=lambda key, *a, **kw: settings[key])


class _McpUser:
    def __init__(self, viewer):
        self.viewer = viewer

    def can_access(self, permission, entity=None, person=None):
        return self.viewer and permission == 'ViewSettingsInterfaceAdmin'


class TestMcpWriteAllowed:

    @pytest.mark.parametrize('viewer,for_viewers,for_others,expected', [
        (True, True, False, True),
        (True, False, True, False),
        (False, True, False, False),
        (False, False, True, True),
        (True, False, False, False),
        (False, False, False, False),
        (True, True, True, True),
        (False, True, True, True),
    ])
    def test_flags_follow_settings_view_permission(self, viewer, for_viewers, for_others, expected):
        settings = {
            'AllowMcpWriteForSettingsViewers': for_viewers,
            'AllowMcpWriteForNonSettingsViewers': for_others,
        }
        with patch.object(SettingsService, 'get_setting', side_effect=lambda key, *a, **kw: settings[key]):
            assert SettingsService.mcp_write_allowed(_McpUser(viewer)) is expected

    def test_missing_user_is_denied(self):
        assert SettingsService.mcp_write_allowed(None) is False


class TestIsOfflineMobileAppEnabled:

    @pytest.mark.parametrize('platform_type,offline_mobile_app,expected', [
        ('new-premium', True, True),
        ('new-premium', False, False),
        ('new-premium', MISSING, True),
        ('features-package', True, True),
        ('features-package', False, False),
        ('features-package', MISSING, False),
        ('premium', True, True),
        ('premium', False, False),
        ('premium', MISSING, True),
        ('freemium-demo', True, True),
        ('freemium-demo', False, False),
        ('freemium-demo', MISSING, True),
        ('some-other-type', False, False),
        ('some-other-type', MISSING, True),
    ])
    def test_is_offline_mobile_app_enabled(self, platform_type, offline_mobile_app, expected):
        with patch_offline_mobile_app_settings(platform_type, offline_mobile_app):
            assert SettingsService.is_offline_mobile_app_enabled() is expected
