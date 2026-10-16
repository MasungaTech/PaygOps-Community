from datetime import datetime
from pony.orm import db_session, commit
from mock import patch

from tests.base_test import BaseViewJsonTest
from accounting_system.account.services.services import AccountDashboard

from accounting_system.account.views.reports import get_interval_dates


class TestReportDataView(BaseViewJsonTest):
    url = 'account.dashboard_data'

    def test_data_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code

    @patch.object(AccountDashboard, 'data', return_value={})
    def test_data_returns_account_data(self, dashboard, super_admin_app):
        response = self.get(super_admin_app)
        expected_data = {}

        assert expected_data == response.json_data


class TestReportTurnoverData(BaseViewJsonTest):
    url = 'account.turnover_chart_data'

    def test_data_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code

    def test_returns_turnover_data(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 'data' in response.json_data
        assert 'datasets' in response.json_data['data']
        assert 'Turnover' in response.json_data['data']['datasets'][0]['label']


class TestReportRevenueChangeData(BaseViewJsonTest):
    url = 'account.revenue_change_chart_data'

    def test_data_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code

    def test_returns_revenue_change_data(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 'data' in response.json_data
        assert 'datasets' in response.json_data['data']
        assert 'Monthly Revenue Change' in response.json_data['data']['datasets'][0]['label']


class TestReportExpensesData(BaseViewJsonTest):
    url = 'account.expenses_chart_data'

    def test_data_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code

    def test_returns_expenses_data(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 'data' in response.json_data
        assert 'datasets' in response.json_data['data']
        assert 'Expenses' in response.json_data['data']['datasets'][0]['label']


class TestReportIncomeData(BaseViewJsonTest):
    url = 'account.income_data'

    def test_data_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code

    def test_returns_income_data(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 'data' in response.json_data
        assert 'datasets' in response.json_data['data']
        assert 'Income' in response.json_data['data']['datasets'][0]['label']


class TestTurnoverChangeData(BaseViewJsonTest):
    url = 'account.turnover_change_data'

    def test_data_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code

    def test_returns_turnover_change_data(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 'data' in response.json_data
        assert 'datasets' in response.json_data['data']
        assert 'RevenueChange' in response.json_data['data']['datasets'][0]['label']


class TestTurnoverPerCustomerData(BaseViewJsonTest):
    url = 'account.turnover_per_customer_data'

    def test_data_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code

    def test_returns_turnover_per_customer_data(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 'data' in response.json_data
        assert 'datasets' in response.json_data['data']
        assert 'Turnover' in response.json_data['data']['datasets'][0]['label']


class TestNumberOfPaymentsData(BaseViewJsonTest):
    url = 'account.number_of_payments_data'

    def test_data_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code

    def test_returns_number_of_payments_data(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 'data' in response.json_data
        assert 'datasets' in response.json_data['data']
        assert 'Payments' in response.json_data['data']['datasets'][0]['label']


class TestReceiptTypeData(BaseViewJsonTest):
    url = 'account.receipt_type_data'

    def test_data_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code

    def test_returns_receipt_type_data(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 'data' in response.json_data
        assert 'datasets' in response.json_data['data']
        assert 'ReceiptType' in response.json_data['data']['datasets'][0]['label']

