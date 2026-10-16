from datetime import datetime, time
from dateutil import tz
from shared.services.settings_service import SettingsService


class Clock:
    ISO_PATTERN = "%Y-%m-%dT%H:%M:%S.%f"
    UTC_INDICATOR = "Z"

    @classmethod
    def now(cls):
        return datetime.now().isoformat() + cls.UTC_INDICATOR

    @classmethod
    def complies_iso8601(cls, timestamp):
        return cls._is_convertible_in_datetime(timestamp)

    @classmethod
    def to_datetime(cls, timestamp):
        iso_pattern = cls.ISO_PATTERN + cls.UTC_INDICATOR

        return datetime.strptime(timestamp, iso_pattern)

    @classmethod
    def to_timestamp(cls, datetime):
        sliced = datetime.strftime(cls.ISO_PATTERN)[0:-3]

        return sliced + cls.UTC_INDICATOR

    @classmethod
    def localize(cls, dt, from_zone=None, to_zone=None, naive=False):

        if not dt:
            return None

        from_zone_obj = cls._get_zone(from_zone)
        to_zone_obj = cls._get_zone(to_zone, SettingsService.get_setting('TargetTimezone'))

        # if dt is a date object it wont be of class datetime but not the other way round
        # because of class inheritance
        if not isinstance(dt, datetime):
            dt = datetime.combine(datetime.today(), dt) if (
                isinstance(dt, time)) else datetime.combine(dt, time())

        dt = dt.replace(tzinfo=from_zone_obj)
        dt = dt.astimezone(to_zone_obj)

        if naive:
            dt = dt.replace(tzinfo=None)

        return dt

    @staticmethod
    def _get_zone(name, default=None):
        if not default:
            default = 'UTC'
        return tz.gettz(name) if name else tz.gettz(default)

    @classmethod
    def localize_to_utc(cls, dt, naive=False):

        return cls.localize(dt, SettingsService.get_setting('TargetTimezone'), 'UTC', naive)

    @classmethod
    def _is_convertible_in_datetime(cls, timestamp):
        result = False

        try:
            cls.to_datetime(timestamp)
        except (ValueError, TypeError):
            pass
        else:
            result = True

        return result
