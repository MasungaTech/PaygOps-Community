import dateutil.parser
import dateutil.relativedelta
import pytest
import mock
from datetime import datetime, timedelta, timezone, date
from pony.orm import db_session
from shared.helpers import date_helper
from shared.helpers.iso_week import Week

from shared.helpers.week_helper import WeekService


class TestDateHelper:

    def assertTzInfo(self, d, shallContainUtcInfo=False):

        if shallContainUtcInfo:
            assert d.tzinfo == timezone.utc
        else:
            assert not d.tzinfo

    def test_addUtcTzInfo(self):
        d = self.getTestDate()
        d = date_helper.addUtcTzInfo(d)

        assert isinstance(d, datetime)
        self.assertTzInfo(d, True)

    def test_getCurrentUtcDate(self):
        d = date_helper.getCurrentUtcDate()

        # assert d >= self.getRecentDate()
        assert isinstance(d, datetime)
        self.assertTzInfo(d)

    @pytest.mark.skip('This test is variable and only passes on local builds, not on CI')
    def test_getCurrentUtcDateAsISOString(self):
        dstr = date_helper.getCurrentUtcDateAsISOString()

        d = dateutil.parser.parse(dstr, ignoretz=True)
        recentD = self.getRecentDate()

        assert isinstance(dstr, str)
        assert d < recentD
        self.assertTzInfo(d)

    def test_formatDateStringToDate(self):
        dstr = self.getTestDateStr()
        d = date_helper.formatDateStringToDate(dstr)

        assert d
        assert isinstance(d, datetime)
        assert str(d) == self.getTestDateStr()
        self.assertTzInfo(d)

    def test_formatISODateStringToDate(self):
        dstr = '2016-01-01T00:00:00Z'
        d = date_helper.formatDateStringToDate(dstr)

        assert d
        assert isinstance(d, datetime)
        assert str(d) == self.getTestDateStr()
        self.assertTzInfo(d)

    def test_formatDateToISODateStr(self):
        d = self.getTestDate()
        dstr = date_helper.formatDateToUTCISODateStr(d)

        parsedD = dateutil.parser.parse(dstr)

        assert isinstance(dstr, str)
        assert parsedD  # could parse the date?

        # check ISO format is like 2004-06-14T23:34:30Z
        assert 'T' in dstr
        assert dstr.endswith('Z')

    def test_from_str_to_datetime_returns_date(self):
        assert date(2017, 1, 1) == date_helper.from_str_to_date('2017-01-01')

    def test_from_str_to_datetime_returns_today_date(self):
        assert date.today() == date_helper.from_str_to_date('2017-13-01')

    def test_interval_dates_returns_complete_date(self):
        str_dates = date_helper.interval_dates(date(2017, 1, 1),
                                               date(2017, 1, 2),
                                               frequency='d')

        assert ['2017-01-01', '2017-01-02'] == str_dates

    def test_interval_dates_returns_list_of_complete_dates(self):
        str_dates = date_helper.interval_dates(date(2017, 1, 1),
                                               date(2017, 1, 15),
                                               frequency='w')

        assert ['2017-01-01', '2017-01-08', '2017-01-15'] == str_dates

    def test_interval_dates_returns_list_of_month_and_year_dates(self):
        str_dates = date_helper.interval_dates(date(2017, 1, 1),
                                               date(2017, 3, 20))

        assert ['Jan 2017', 'Feb 2017', 'Mar 2017'] == str_dates

    def test_get_index_by_monthly_frequency(self):
        index = date_helper.get_index_by_date_frequency(date(2017, 1, 1),
                                                        frequency='m')

        assert 'Jan 2017' == index

    def test_get_index_by_weekly_frequency(self):
        index = date_helper.get_index_by_date_frequency(date(2017, 1, 1),
                                                        frequency='w')

        assert '2017-01-01' == index

    def test_get_index_by_daily_frequency(self):
        index = date_helper.get_index_by_date_frequency(date(2017, 1, 1),
                                                        frequency='d')

        assert '2017-01-01' == index


    def getTestDate(self, addUtcInfo=False):
        dt = datetime(2016, 1, 1, 0, 0, 0)
        if addUtcInfo:
            dt = date_helper.addUtcTzInfo(dt)
        return dt

    def getTestDateStr(self):
        return str(self.getTestDate())

    def getRecentDate(self, addUtcInfo=False):
        d = datetime.now().replace(microsecond=0)
        if addUtcInfo:
            d = date_helper.addUtcTzInfo(d)
        return d - timedelta(seconds=2)

    def getRecentDateStr(self):
        return str(self.getRecentDate())


def test_monthly_difference():
    today = datetime.today()
    month_ago = today - dateutil.relativedelta.relativedelta(months=3)
    start_period = datetime(month_ago.year, month_ago.month, 1)

    res = date_helper.DateDifferenceService.monthly_diff(today, start_period)
    assert res in range(3, 5)

    res = date_helper.DateDifferenceService.monthly_diff(today, None)
    assert res is None


def test_weekly_difference():
    end = datetime.today()
    past_date = end - dateutil.relativedelta.relativedelta(months=3)
    start = datetime(past_date.year, past_date.month, 1)

    res = date_helper.DateDifferenceService.get_weekly_difference(start, end)

    assert res in range(13, 19)

@db_session
def test_get_weeks_before():
    week = Week(2017, 20)

    res = WeekService._get_datetime_week_before(week, 3)

    assert res.year == 2017
    assert res.month == 4
    assert res.day == 24


def test_get_daily_difference():
    today = datetime.today()
    past_date = today - timedelta(days=5)

    res = date_helper.DateDifferenceService.number_of_days_in_between(past_date, today)

    assert res == 6


def test_month_date_range():
    month = [1, 2, 4]
    year = [2000, 2001]

    ranges = date_helper.month_date_range

    assert ranges(month[0], year[0]) == (date(2000, 1, 1), date(2000, 1, 31))
    assert ranges(month[2], year[0]) == (date(2000, 4, 1), date(2000, 4, 30))
    assert ranges(month[1], year[0]) == (date(2000, 2, 1), date(2000, 2, 29))
    assert ranges(month[1], year[1]) == (date(2001, 2, 1), date(2001, 2, 28))


@mock.patch('shared.helpers.date_helper.datetime')
def test_time_since_date(mock_datetime):
    mock_datetime.now = mock.Mock(return_value=datetime(2005, 1, 1))
    time_since = date_helper.get_time_since_date(date(2000, 1, 1))
    time_since_months = date_helper.get_time_since_date(date(2004, 6, 1), months=True)
    time_since_years = date_helper.get_time_since_date(date(2004, 1, 1), years=True)

    assert time_since_months == 7
    assert time_since_years == 1
    assert time_since.years == 5
