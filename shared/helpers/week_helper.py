from datetime import datetime
from isoweek import Week

from shared.services.settings_service import SettingsService


class WeekService:

    @classmethod
    def get_weekly_date(cls, weeks_before=0):
        weeks_before = weeks_before - 1
        week = Week.thisweek()
        return cls._get_datetime_week_before(week, weeks_before)

    @staticmethod
    def _get_datetime_week_before(week, weeks_before):
        if week.day(SettingsService.get_setting('FirstDayOfWeek')) > datetime.now().date():  # We check if we should start this week or the week before?
            w = week - 1 - weeks_before  # We do from Friday to Friday
        else:
            w = week - weeks_before
        date = w.day(SettingsService.get_setting('FirstDayOfWeek'))
        return datetime(date.year, date.month, date.day).date()
