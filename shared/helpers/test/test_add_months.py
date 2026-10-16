from shared.helpers.date_helper import add_months
from datetime import datetime


class TestAddMonthsHelper:

    def test_add_months_helper(self):
        assert add_months(datetime(2021, 2, 28), 1) == datetime(2021, 3, 28)
