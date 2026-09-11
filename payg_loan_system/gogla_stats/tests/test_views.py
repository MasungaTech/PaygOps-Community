from tests.base_test import BaseViewJsonTest, BaseViewTest
from payg_loan_system.gogla_stats.gather import run_gogla_stats


class TestRecentPortfolioFigure(BaseViewJsonTest):
    url = 'historical_data.recent_portfolio_figure'
    run_gogla_stats()

    def test_recent_portfolio_figure(self, super_admin_app):
        res = self.get(super_admin_app)

        assert res.json_data


class TestRecentAverageCreditPeriod(BaseViewJsonTest):
    url = 'historical_data.recent_average_credit_period'
    run_gogla_stats()

    def test_recent_portfolio_figure(self, super_admin_app):
        res = self.get(super_admin_app)

        assert res.json_data


class TestGoglaDashboard(BaseViewTest):
    url = 'historical_data.gogla_dashboard'
    template = 'gogla.html'

