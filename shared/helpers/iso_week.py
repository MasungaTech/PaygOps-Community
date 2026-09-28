from datetime import date, timedelta


class Week:
    """ISO 8601 week (Monday–Sunday), compatible with the former isoweek API."""

    __slots__ = ('year', 'week')

    def __init__(self, year, week):
        monday = date.fromisocalendar(year, week, 1)
        iso_year, iso_week, _ = monday.isocalendar()
        self.year = iso_year
        self.week = iso_week

    @classmethod
    def thisweek(cls):
        iso_year, iso_week, _ = date.today().isocalendar()
        return cls(iso_year, iso_week)

    def day(self, day_index):
        return date.fromisocalendar(self.year, self.week, day_index + 1)

    def __sub__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        monday = date.fromisocalendar(self.year, self.week, 1)
        monday -= timedelta(weeks=other)
        iso_year, iso_week, _ = monday.isocalendar()
        return Week(iso_year, iso_week)

    def __repr__(self):
        return f'Week({self.year}, {self.week})'
