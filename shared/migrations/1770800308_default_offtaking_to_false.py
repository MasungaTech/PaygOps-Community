from pony.orm import db_session
from shared.services.settings_service import SettingsService

@db_session
def up(db):
    feature_toggles = SettingsService.get_setting('FeatureToggles')
    feature_toggles['OffTaking'] = False
    SettingsService.set_setting('FeatureToggles', feature_toggles)

@db_session
def down(db):
    feature_toggles = SettingsService.get_setting('FeatureToggles')
    feature_toggles['OffTaking'] = True
    SettingsService.set_setting('FeatureToggles', feature_toggles)
