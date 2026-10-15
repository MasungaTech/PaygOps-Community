import json
from datetime import datetime
from pony.orm import db_session

from .model import HistoricalData


def save_historical_data(data_type, value, org_id):
    val = json.dumps(dict(value=value))
    if data_type in ['portfolio_size',
                     'revenue_average',
                     'average_credit_period',
                     'average_unit_cost',
                     'deposit_as_proportion_cost',
                     'compliance_percentage',
                     'churn_rate']:

        return save_gogla_data(data_type, val, org_id)
    else:
        raise ValueError('Data type {} is not supported'.format(data_type))


def save_gogla_data(data_type, value, org_id):
    params = dict(type=data_type,
                  content=value,
                  organization_id=org_id,
                  calculated_on=datetime.now())
    return insert_historical_data(**params)


@db_session
def insert_historical_data(**kwargs):
    return HistoricalData(**kwargs)
