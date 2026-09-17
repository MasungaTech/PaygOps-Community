from datetime import datetime, timedelta
from shared.helpers.iso_week import Week
from shared.services.settings_service import SettingsService


def getWeekDate(weeks_before=0):
    weeks_before = weeks_before - 1
    if Week.thisweek().day(SettingsService.get_setting('FirstDayOfWeek')) > datetime.now().date():  # We check if we should start this week or the week before?
        date = (Week.thisweek() - 1 - (weeks_before)).day(SettingsService.get_setting('FirstDayOfWeek'))
    else:
        date = (Week.thisweek() - (weeks_before)).day(SettingsService.get_setting('FirstDayOfWeek'))
    date = datetime(date.year, date.month, date.day)
    return date


def getMonthDate(months_before=0):
    months_before = months_before - 1
    today = datetime.today()
    y = today.year + ((today.month) - months_before - 1) // 12
    m = (today.month - months_before) % 12
    if not m:
        m = 12
    d = 1
    return datetime(y, m, d)


def getMonthDifference(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month


def getWeekDifference(d1, d2):
    monday1 = (d1 - timedelta(days=d1.weekday()))
    monday2 = (d2 - timedelta(days=d2.weekday()))
    diff = int((monday2 - monday1).days / 7)
    return diff
