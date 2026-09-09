from datetime import datetime
from mock import MagicMock
from accounting_system.account.services.services import AccountDashboard
from data_system.old_system.stats import StatsEngine


class TestAccountDashboard:
    def test_returns_dashboard_data(self):
        start_date = datetime.today()
        end_date = datetime.today()

        expected = {
            'total_turnover': 0,
            'average_turnover': 0,
            'number_of_payments': 0,
            'account_receivable': 0,
            'average_account_receivable_per_client': 0,
            'current_account_receivable': 0
        }

        stats_engine = StatsEngine()
        stats_engine.generate_account_data = MagicMock(return_value=self._data())

        assert expected == AccountDashboard.data(start_date,
                                                 end_date,
                                                 stats_engine)

    def _data(self):
        return {
            'total_turnover': 0,
            'average_turnover': 0,
            'number_of_payments': 0,
            'account_receivable': 0,
            'average_account_receivable_per_client': 0,
            'current_account_receivable': 0
        }
