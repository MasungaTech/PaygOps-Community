from datetime import datetime, timedelta
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService


def validate_planned_delivery_dates(proposed_date, user):
    if user.can_access('OverrideDeliveryDateLimitsLeads') or not SettingsService.get_setting('EnableLimitOnPlannedDeliveryDate'):
        return
    before_limit = SettingsService.get_setting('BeforeLimitOnPlannedDeliveryDate')
    after_limit = SettingsService.get_setting('AfterLimitOnPlannedDeliveryDate')
    if proposed_date.date() < (datetime.now() - timedelta(days=before_limit)).date():
        raise Error('Planned delivery date should not be more than {before_limit} days before now', before_limit=before_limit, force_format=True)
    if after_limit and (proposed_date.date() > (datetime.now() + timedelta(days=after_limit)).date()):
        raise Error('Planned delivery date should not be more than {after_limit} days from now', after_limit=after_limit, force_format=True)