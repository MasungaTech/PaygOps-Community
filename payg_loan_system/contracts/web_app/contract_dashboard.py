from constants import CLIENT_VIEWS
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from flask_login import login_required, current_user
from flask import render_template, request, redirect, url_for
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from shared.services.settings_service import SettingsService
from . import contract
from payg_loan_system.contracts.services.contract_stats_service import ContractStatsService
from data_system.services.graph_service import GraphService
from data_system.services.custom_dashboard_service import CustomDashboardService


@contract.route('/dashboard', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@db_session
def view_contract_dashboard():
    replaces_default = CustomDashboardService.replaces_default('contract')
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    if replaces_default:
        return redirect(url_for('overview.view_custom_dashboard', dashboard_name='contract', entity_id=getattr(entity,'id',None), portfolio_id=getattr(portfolio,'id',None)))
    else:
        return redirect(url_for('contract.view_contract_dashboard_default', entity_id=getattr(entity,'id',None), portfolio_id=getattr(portfolio,'id',None)))


@contract.route('/dashboard/default', methods=['GET', 'POST'])
@login_required
@authorizer('ViewDashboards')
@db_session
def view_contract_dashboard_default():

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    client_group = ClientGroupGetterService.extract_from_user_and_id(current_user, request.args, "client_group_id", strict=False)
    view = request.args.get('view', 'all')

    from_time = GraphService.process_input_time(request.form.get('from_time', None), from_time=True)
    from_time_raw = GraphService.process_input_time(request.form.get('from_time', None), from_time=True, localize=False)
    to_time = GraphService.process_input_time(request.form.get('to_time', None), from_time=False, localize=False)
    to_time_raw = GraphService.process_input_time(request.form.get('to_time', None), from_time=False, localize=False)

    if not SettingsService.get_setting('StressMode'):
        contracts = ContractGetterService.get_from_filtered_view(
            current_user.reload(),
            view=view,
            entity=entity,
            portfolio=portfolio,
            client_group=client_group
        )

        customer_traction_graph_data = GraphService.generate_monthly_graph_data(
            from_time=from_time,
            to_time=to_time,
            value_function=ContractStatsService.get_number_of_non_defaulted_contracts_in_period,
            value_function_2=ContractStatsService.get_number_of_new_contracts_in_period,
            value_function_3=ContractStatsService.get_number_of_defaulted_contract_in_period,
            contracts=contracts
        )

        default_graph_data = GraphService.generate_monthly_graph_data(
            from_time=from_time,
            to_time=to_time,
            value_function=ContractStatsService.get_default_rate_in_period,
            contracts=contracts
        )

        par_graph_data = ContractStatsService.get_par_data(contracts)
    else:
        customer_traction_graph_data = None
        default_graph_data = None
        par_graph_data = None

    return render_template(
        'view_contract_dashboard.html',
        from_time=from_time_raw,
        to_time=to_time_raw,
        customer_traction_graph_data=customer_traction_graph_data,
        default_graph_data=default_graph_data,
        par_graph_data=par_graph_data,
        entity=entity,
        view=view,
        views=CLIENT_VIEWS
    )


