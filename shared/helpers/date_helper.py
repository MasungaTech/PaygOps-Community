import random
import calendar
from datetime import datetime, timezone, timedelta, date
import datetime as _datetime
from decimal import Decimal
from dateutil.rrule import rrule, MONTHLY, DAILY, WEEKLY, HOURLY
import dateutil.parser
from dateutil.relativedelta import relativedelta
from shared.logger.loggers import Error
from mock import patch
from functools import wraps
from flask import request, jsonify


def timedelta_to_hours(td):
    return Decimal(td.days*24 + td.seconds/3600 + td.microseconds*1e-6/3600)


def timedelta_to_seconds(td):
    return Decimal(td.days*24*3600 + td.seconds + td.microseconds*1e-6)


def days_until_date(this_date, time=None):
    if not time:
        time = datetime.now()
    td = this_date - time
    return timedelta_to_hours(td)/Decimal(24)


def age_from_birthdate(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def addUtcTzInfo(dt):
    dt = dt.replace(tzinfo=timezone.utc)
    return dt


def getCurrentUtcDate(isAddUtcTzInfo=False):
    dt = datetime.now()

    if isAddUtcTzInfo:
        dt = addUtcTzInfo(dt)
    return dt


def getCurrentUtcDateAsISOString():
    return formatDateToUTCISODateStr(getCurrentUtcDate())


def formatDateStringToDate(dateStr, isAddUtcTzInfo=False):
    if not dateStr:
        return
    # use dateutil parser here because it can parse ISO 8601 format
    dt = dateutil.parser.parse(dateStr, ignoretz=not isAddUtcTzInfo)
    if isAddUtcTzInfo:
        dt = addUtcTzInfo(dt)

    return dt


def formatDateToUTCISODateStr(date):
    if not date:
        return None

    # javascript uses different ISO format by default than python
    pythonISODateStr = date.isoformat()
    javascriptISODateStr = pythonISODateStr.replace('+00:00', '')
    if not javascriptISODateStr.endswith('Z'):
        javascriptISODateStr += 'Z'
    return javascriptISODateStr


def getDefaultDate():
    return datetime.now()


def getDefaultDateStr():
    return getDefaultDate().isoformat()


def from_str_to_date(str_date, format='%Y-%m-%d'):
    try:
        return datetime.strptime(str_date, format).date()
    except:
        return date.today()


def from_str_to_datetime(str_date, format='%Y-%m-%d'):
    try:
        return datetime.strptime(str_date, format)
    except:
        return datetime.today()


def interval_dates(start_date, end_date, frequency='m'):
    if frequency == '6h':
        dates = rrule(HOURLY, dtstart=start_date, until=end_date, byhour=[0,6,12,18,24])
        return [get_index_by_date_frequency(dt, 'h') for dt in dates]

    if frequency == 'h':
        dates = rrule(HOURLY, dtstart=start_date, until=end_date)
        return [get_index_by_date_frequency(dt, frequency) for dt in dates]

    if frequency == 'd':
        dates = rrule(DAILY, dtstart=start_date, until=end_date)
        return [get_index_by_date_frequency(dt, frequency) for dt in dates]

    if frequency == 'w':
        dates = rrule(WEEKLY, dtstart=start_date, until=end_date)
        return [get_index_by_date_frequency(dt, frequency) for dt in dates]

    if frequency == 'm':
        dates = rrule(MONTHLY, dtstart=start_date, until=end_date)

    return [get_index_by_date_frequency(dt, frequency) for dt in dates]


def interval_dates_list(start_date, end_date, frequency='m'):
    dates = []

    if frequency == 'd':
        dates = rrule(DAILY, dtstart=start_date, until=end_date)

    if frequency == 'w':
        dates = rrule(WEEKLY, dtstart=start_date, until=end_date)

    if frequency == 'm':
        dates = rrule(MONTHLY, dtstart=start_date, until=end_date)

    return dates


def get_index_by_date_frequency(index_date, frequency='m'):
    if frequency == 'h':
        index = index_date.strftime('%Y-%m-%d %H:00:00')

    if frequency == 'd':
        index = index_date.strftime('%Y-%m-%d')

    if frequency == 'w':
        week = index_date.strftime('%Y-W%W-0')
        week = _datetime.datetime.strptime(week, "%Y-W%W-%w")

        index = week.strftime('%Y-%m-%d')

    if frequency == 'm':
        index = index_date.strftime('%b %Y')

    return index


def get_last_datetime_of_date_label(index, frequency='m'):
    if frequency == 'd':
        return datetime.strptime(index, '%Y-%m-%d')
    elif frequency == 'w':
        return datetime.strptime(index, '%Y-%m-%d')
    elif frequency == 'm':
        return datetime.strptime(index, '%b %Y')


def first_of_this_month():
    return datetime.now().replace(day=1, hour=0, minute=0)


def last_day_of_month(date):
    return date.replace(day=calendar.monthrange(date.year, date.month)[1],
                        hour=23,
                        minute=59,
                        second=59)


def ninety_days_from_today():
    return datetime.now()-timedelta(days=90)


def hundred_eighty_days_from_today():
    return datetime.now()-timedelta(days=180)


def ninety_days_from_first_of_month():
    return first_of_this_month() - timedelta(days=90)


def first_of_last_month():
    today = datetime.now().replace(hour=0, minute=0, second=0)
    return today.replace(day=1)


def parse_datetime(str):
    if not str:
        return
    try:
        return dateutil.parser.parse(str).replace(tzinfo=None)
    except (ValueError, TypeError, dateutil.parser._parser.ParserError):
        raise Error('Invalid date format "'+str+'"')
    # return first - timedelta(days=1)


class DateDifferenceService:
    @staticmethod
    def get_monthly_date(months_before=0):
        months_before = months_before - 1
        today = datetime.today()
        return DateDifferenceService._get_datetime_month_before(today, months_before)

    @staticmethod
    def _get_datetime_month_before(today, months_before):
        y = today.year + (today.month - months_before - 1) // 12
        m = (today.month - months_before) % 12
        if not m:
            m = 12
        d = 1
        return datetime(y, m, d)

    @staticmethod
    def get_weekly_difference(d1, d2):
        monday1 = (d1 - timedelta(days=d1.weekday()))
        monday2 = (d2 - timedelta(days=d2.weekday()))
        mon_diff = monday2 - monday1
        mon_diff_days = mon_diff.days
        week = mon_diff_days / 7
        return round(week)

    @staticmethod
    def monthly_diff(d1, d2):
        if d1 and d2:
            return (d1.year - d2.year) * 12 + d1.month - d2.month
        return None

    @staticmethod
    def daily_difference(start, end):
        span = end - start
        days = round(span.days + 1)
        for i in range(days):
            yield start + timedelta(days=i)

    @staticmethod
    def number_of_days_in_between(start, end):
        return len(list(DateDifferenceService.daily_difference(start, end)))


def random_date(start_day=1, end_day=28, start_month=1, end_month=12, start_year=2015, end_year=datetime.now().year):
    year = random.randint(start_year, end_year)
    month = random.randint(start_month, end_month)
    day = random.randint(start_day, end_day)
    date = '%s-%s-%s' % (year, month, day)
    return datetime.strptime(date, '%Y-%m-%d')


def parse_date(date): # TODO:Implement for other date formats
    """
    Parse d/m/y string to date object
    :param date: str d/m/y
    :return: date object
    """
    return datetime.strptime(date, '%Y-%m-%d').date()


def month_date_range(month, year):
    """
    Returns the beginning and the end date for any month of a given year
    :param month:
    :param year:
    :return: Tuple since_date, to_date:

             since_date : Beginning date of the month (year/month/day)
             to_date : End date of the month (year/month/day)
    """
    month_days = calendar.monthrange(year, month)[1]
    since = '%s-%s-01' % (year, month)
    to = '%s-%s-%s' % (year, month, month_days)
    since_date = parse_date(since)
    to_date = parse_date(to)
    return since_date, to_date


def get_time_since_date(date, months=False, years=False):  # TODO:Implement for days
    """
    Time in days|months|years since a given date
    :param date: in .date() format
    :param months: bool True to return months past since date
    :param years: bool True to return months past since date
    :return: int | relativedelta
    """
    total_time = relativedelta(datetime.now().date(), date)
    if months:
        return total_time.months + (total_time.years * 12)
    elif years:
        return total_time.years

    return total_time

def add_months(date, months):
    full_months = int(months)
    remainder = months - full_months
    new_date = date + relativedelta(months=+full_months)
    if remainder:
        month_days = calendar.monthrange(new_date.year, new_date.month)[1]
        hours_to_add = month_days*remainder*24
        return new_date + timedelta(hours=float(hours_to_add))
    return new_date

def get_days_in_month(date):
    return calendar.monthrange(date.year, date.month)[1]

def set_day_of_month(date, day_of_month):
    new_date = date + relativedelta(day=day_of_month)
    return new_date


# --- Custom Date Decorator

from freezegun import freeze_time

def use_custom_date(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        import config
        custom_date_allowed = config.is_test_platform()
        custom_date_header = request.headers.get('X-Custom-Date')
        if custom_date_header:
            if not custom_date_allowed:
                return jsonify({'error': 'X-Custom-Date header is forbidden on this platform'}), 400
            try:
                custom_date = datetime.fromisoformat(custom_date_header)
            except ValueError:
                return jsonify({'error': 'Invalid date format in X-Custom-Date header'}), 400
            
            with freeze_time(custom_date):
                return func(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper