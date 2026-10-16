import json
from pony.orm import db_session
from payg_loan_system.gogla_stats.model import RevenueAverage, HistoricalData
from payg_loan_system.gogla_stats.helpers import save_historical_data


class TestRevenueAverage:
    content = {
        'recent_average': 21935,
        'average_list': [
            {'month': 'Mar 2017', 'amount': 7803, 'position': 11},
            {'month': 'Apr 2017', 'amount': 8324, 'position': 10},
            {'month': 'May 2017', 'amount': 9548, 'position': 9},
            {'month': 'Jun 2017', 'amount': 9995, 'position': 8},
            {'month': 'Jul 2017', 'amount': 11206, 'position': 7},
            {'month': 'Aug 2017', 'amount': 14477, 'position': 6},
            {'month': 'Sep 2017', 'amount': 14222, 'position': 5},
            {'month': 'Oct 2017', 'amount': 18120, 'position': 4},
            {'month': 'Nov 2017', 'amount': 19483, 'position': 3},
            {'month': 'Dec 2017', 'amount': 20826, 'position': 2},
            {'month': 'Jan 2018', 'amount': 21935, 'position': 1}
        ]
    }

    def test_most_recent_revenue_average_without_data(self):
        assert '0' == str(RevenueAverage.recent_amount())

    def test_most_recent_revenue_average_returns_zero(self):
        save_historical_data('revenue_average', json.dumps({}), 'test')

        assert '0' == str(RevenueAverage.recent_amount())

    def test_most_recent_revenue_average_returns_0(self):
        save_historical_data('revenue_average',
                             json.dumps({
                                'average_list': [], 'recent_average': 0}
                             ), 'test')

        assert '0' == RevenueAverage.recent_amount()

    def test_most_recent_returns_21935(self):
        save_historical_data('revenue_average',
                             json.dumps(self.content),
                             'test')

        assert '21,935' == RevenueAverage.recent_amount()

    def test_most_recent_average_list_returns_list(self):
        assert self.content['average_list'] == RevenueAverage.recent_average_list()

    @db_session
    def test_most_recent_data_response(self):
        historical_data = list(HistoricalData.select(
            lambda h: h.type == 'revenue_average'))[-1]

        data = RevenueAverage.recent_data_response()

        assert historical_data.calculated_on.strftime('%Y-%m-%d') == data.get('calculated_on')
        assert '21,935 USD' == data.get('amount')

    @db_session
    def test_most_recent_average_list_returns_empty(self):
        HistoricalData.select(lambda h: h.type == 'revenue_average').delete()

        assert [] == RevenueAverage.recent_average_list()
