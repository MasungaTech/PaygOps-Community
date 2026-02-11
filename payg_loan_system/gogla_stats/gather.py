import json
from core_system.client.services.other_services import ClientPortfolioStats
from payg_loan_system.gogla_stats.helpers import save_historical_data
from payg_loan_system.gogla_stats.model import RevenueAverage
from pony.orm import db_session


@db_session
def run_gogla_stats():
    stats = ClientPortfolioStats()

    kpis = {'portfolio_size': stats.active_contract_count,
            'average_credit_period': stats.average_active_clients_credit_period,
            'compliance_percentage': stats.get_device_compliance_percentage,
            'average_unit_cost': stats.average_unit_cost,
            'deposit_as_proportion_cost': stats.average_customer_deposit_by_cost,
            'churn_rate': stats.get_churn_rate}

    for kpi, method in kpis.items():
        save_historical_data(kpi, method(), 'Gogla')

    average_list = RevenueAverage.generate_data(stats)
    save_historical_data('revenue_average', json.dumps(average_list), 'Gogla')

if __name__ == '__main__':
    run_gogla_stats()
