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
