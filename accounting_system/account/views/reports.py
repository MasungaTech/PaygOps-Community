from datetime import datetime, timedelta
from flask import request, jsonify
from flask_login import login_required
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from shared.helpers.clock import Clock
from accounting_system.account import account
from accounting_system.account.services.services import AccountDashboard
from data_system.old_system.stats_helper import StatsHelper
from shared.helpers.chart import ChartService, GroupedLabels


@account.route('/dashboard/data', methods=['GET'])
@login_required
@authorizer('ViewGlobalDashboards', 'index')
@db_session
def dashboard_data():
    start_date, end_date = get_interval_dates(request)

    return jsonify(AccountDashboard.data(start_date, end_date))


@account.route('/dashboard/turnover_chart_data', methods=['GET'])
@login_required
@authorizer('ViewGlobalDashboards', 'index')
@db_session
def turnover_chart_data():
    start_date, end_date = get_interval_dates(request)

    stats_helper = StatsHelper()
    turnover_data = stats_helper.GetTurnoverChartData(start_date, end_date)
    return generate_chart_data(turnover_data, 'Turnover')


@account.route('/dashboard/revenue_chart_data', methods=['GET'])
@login_required
@authorizer('ViewGlobalDashboards', 'index')
@db_session
def revenue_change_chart_data():
    start_date, end_date = get_interval_dates(request)
    stats_helper = StatsHelper()

    revenue_change_data = stats_helper.GetAccountReceivableChartData(
        start_date, end_date)

    return generate_chart_data(revenue_change_data, 'Monthly Revenue Change')


@account.route('/dashboard/expenses_chart_data', methods=['GET'])
@login_required
@authorizer('ViewGlobalDashboards', 'index')
@db_session
def expenses_chart_data():
    start_date, end_date = get_interval_dates(request)
    stats_helper = StatsHelper()

    expenses_data = stats_helper.GetExpensesChartData(start_date, end_date)

    return generate_chart_data(expenses_data, 'Expenses')


@account.route('/dashboard/income_data', methods=['GET'])
@login_required
@authorizer('ViewGlobalDashboards', 'index')
@db_session
def income_data():
    start_date, end_date = get_interval_dates(request)
    stats_helper = StatsHelper()

    income_data = stats_helper.GetIncomeChartData(start_date, end_date)

    return generate_chart_data(income_data, 'Income')


@account.route('/dashboard/revenue_change_data', methods=['GET'])
@login_required
@authorizer('ViewGlobalDashboards', 'index')
@db_session
def turnover_change_data():
    start_date, end_date = get_interval_dates(request)
    stats_helper = StatsHelper()

    turnover_data = stats_helper.GetMonthlyRevenueChangeChartData(start_date, end_date)

    return generate_chart_data(turnover_data, 'RevenueChange')


@account.route('/dashboard/turnover_per_customer_data', methods=['GET'])
@login_required
@authorizer('ViewGlobalDashboards', 'index')
@db_session
def turnover_per_customer_data():
    start_date, end_date = get_interval_dates(request)
    stats_helper = StatsHelper()

    turnover_data = stats_helper.GetRevenuePerCustomerChartData(start_date, end_date)

    return generate_chart_data(turnover_data, 'Turnover')


@account.route('/dashboard/number_of_payments_data', methods=['GET'])
@login_required
@authorizer('ViewGlobalDashboards', 'index')
@db_session
def number_of_payments_data():
    start_date, end_date = get_interval_dates(request)
    stats_helper = StatsHelper()

    payments_data = stats_helper.GetNumberOfPaymentsChartData(start_date, end_date)

    return generate_chart_data(payments_data, 'Payments')


@account.route('/dashboard/receipt_type_data', methods=['GET'])
@login_required
@authorizer('ViewGlobalDashboards', 'index')
@db_session
def receipt_type_data():
    start_date, end_date = get_interval_dates(request)
    stats_helper = StatsHelper()

    payments_data = stats_helper.GetReceiptTypeData(start_date, end_date)

    return generate_chart_data(payments_data, 'ReceiptType')


def generate_chart_data(data, label):
    labels = [d[0] for d in data]
    group = GroupedLabels(labels)

    for d in data:
        group.append(label, d[0], value=d[1])

    return ChartService.generate_response(group)


def get_interval_dates(request):
    if request.args.get('end_date'):
        end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
    else:
        end_date = datetime.today()

    if request.args.get('start_date'):
        start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
    else:
        start_date = end_date - timedelta(days=365)
        
    start_date = Clock.localize_to_utc(start_date)
    end_date = Clock.localize_to_utc(end_date)

    return start_date, end_date
