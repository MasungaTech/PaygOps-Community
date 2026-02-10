from core_system.client.services.other_services import ClientPortfolioStats
import config


def test_number_of_active_clients():
    c = ClientPortfolioStats()
    assert c.active_contract_count()


def test_average_active_clients_credit_period():
    c = ClientPortfolioStats()
    assert c.average_active_clients_credit_period()


def test_average_unit_cost():
    c = ClientPortfolioStats()
    assert c.average_unit_cost()


def test_deposit_by_credit():
    c = ClientPortfolioStats()
    assert c.average_customer_deposit_by_cost()


def test_get_device_compliance_percentage():
    c = ClientPortfolioStats()
    res = c.get_device_compliance_percentage()

    assert res == "0.00%"


def test_get_churn_rate():
    c = ClientPortfolioStats()

    res = c.get_churn_rate()

    assert res == "0.00%"
