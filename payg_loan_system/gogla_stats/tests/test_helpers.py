import pytest

from payg_loan_system.gogla_stats.helpers import save_historical_data, \
    insert_historical_data
from payg_loan_system.gogla_stats.model import HistoricalData


def test_save_historic_portfolio_size():
    res = save_historical_data('portfolio_size', 123, 'Solaris')
    assert isinstance(res, HistoricalData)


def test_save_historic_average_credit_period():
    res = save_historical_data('average_credit_period', 123, 'Solaris')
    assert isinstance(res, HistoricalData)


def test_save_unknown_historic_data():
    with pytest.raises(ValueError) as excinfo:
        save_historical_data('foo', 123, 'Solaris')
    assert 'Data type foo is not supported' in str(excinfo.value)


def test_insert_historic_data():
    with pytest.raises(ValueError) as excinfo:
        insert_historical_data()
    assert ('Attribute' and 'is required') in str(excinfo.value)
