from flask import jsonify
from flask_login import login_required
from pony.orm import db_session

from shared.helpers.authorizer import authorizer

from .. import historical_data
from ..model import HistoricalData, RevenueAverage


@historical_data.route('/chart/portfolio_size/recent')
@login_required
@authorizer('GoglaDashboards')
@db_session
def recent_portfolio_figure():
    data_type = 'portfolio_size'
    data = HistoricalData.most_recent(data_type)

    return jsonify(data.content_dict() if data else {})


@historical_data.route('/chart/average_credit_period/recent')
@login_required
@authorizer('GoglaDashboards')
@db_session
def recent_average_credit_period():
    data_type = 'average_credit_period'
    data = HistoricalData.most_recent(data_type)

    return jsonify(data.content_dict() if data else {})


@historical_data.route('/chart/average_unit_cost/recent')
@login_required
@authorizer('GoglaDashboards')
@db_session
def recent_average_unit_cost():
    data_type = 'average_unit_cost'
    data = HistoricalData.most_recent(data_type)

    return jsonify(data.content_dict() if data else {})


@historical_data.route('/chart/compliance_percentage/recent')
@login_required
@authorizer('GoglaDashboards')
@db_session
def recent_compliance_percentage():
    data_type = 'compliance_percentage'
    data = HistoricalData.most_recent(data_type)

    return jsonify(data.content_dict() if data else {})


@historical_data.route('/chart/deposit-as-proportion-cost/recent')
@login_required
@authorizer('GoglaDashboards')
@db_session
def recent_deposit_by_cost():
    data_type = 'deposit_as_proportion_cost'
    data = HistoricalData.most_recent(data_type)

    return jsonify(data.content_dict() if data else {})


@historical_data.route('/chart/churn_rate/recent')
@login_required
@authorizer('GoglaDashboards')
@db_session
def recent_churn_rate():
    data_type = 'churn_rate'
    data = HistoricalData.most_recent(data_type)

    return jsonify(data.content_dict() if data else {})


@historical_data.route('/chart/revenue_average')
@login_required
@authorizer('GoglaDashboards')
@db_session
def revenue_average():
    return jsonify(RevenueAverage.recent_data_response())
