from constants import CLIENT_VIEWS
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from flask_login import login_required, current_user
from flask import render_template, redirect, url_for, request
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from . import client
from core_system.client.services.client_stats_services import ClientStatsServices
from data_system.services.custom_dashboard_service import CustomDashboardService
from shared.services.settings_service import SettingsService


@client.route('/dashboard', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@db_session
def view_clients_demographics_dashboard():
    replaces_default = CustomDashboardService.replaces_default('demographic')
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    if replaces_default:
        return redirect(url_for('overview.view_custom_dashboard', dashboard_name='demographic', entity_id=getattr(entity,'id',None), portfolio_id=getattr(portfolio,'id',None)))
    else:
        return redirect(url_for('client.view_clients_demographics_dashboard_default', entity_id=getattr(entity,'id',None), portfolio_id=getattr(portfolio,'id',None)))


@client.route('/dashboard/default', methods=['GET', 'POST'])
@login_required
@authorizer('ViewDashboards')
@db_session
def view_clients_demographics_dashboard_default():
    
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    client_group = ClientGroupGetterService.extract_from_user_and_id(current_user, request.args, "client_group_id", strict=False)
    status = request.args.get('status', 'active_contracts')
    view = request.args.get('view', 'all')

    if SettingsService.get_setting('StressMode'):
        return render_template(
            'client_demographic_dashboard.html',
            view=view,
            views=CLIENT_VIEWS,
            entity=entity,
            portfolio=portfolio,
        )

    clients = ClientGetterService.get_from_filtered_view(
        current_user.reload(),
        view=view,
        entity=entity,
        portfolio=portfolio,
        status=status,
        client_group=client_group
    )

    gender_split = ClientStatsServices.get_gender_split(clients)
    gender_chart_data = [('Male', gender_split['male']),
                         ('Female', gender_split['female'])]

    age_split = ClientStatsServices.get_age_split(clients)
    age_chart_data = [
        ('Under 25 yo', age_split['below_25']),
        ('25 to 35 yo', age_split['25_35']),
        ('35 to 45 yo', age_split['35_45']),
        ('45 to 55 yo', age_split['45_55']),
        ('Above 55 yo', age_split['above_55']),
    ]

    business_clients_ratio = ClientStatsServices.get_ratio_of_business_clients(clients)

    average_household_size_computed = ClientStatsServices.get_average_household_size(clients)
    if average_household_size_computed:
        average_household_size = average_household_size_computed
    else:
        average_household_size = 4 # From UN Stats

    number_current_clients = ClientStatsServices.get_number_current_clients(clients)
    number_total_clients = ClientStatsServices.get_total_clients_count(clients)
    number_current_impacted = number_current_clients*average_household_size
    number_total_impacted = number_total_clients * average_household_size

    return render_template(
        'client_demographic_dashboard.html',
        gender_chart_data=gender_chart_data,
        age_chart_data=age_chart_data,
        business_clients_ratio=business_clients_ratio,
        average_household_size_computed=average_household_size_computed,
        average_household_size=average_household_size,
        number_current_clients=number_current_clients,
        number_total_clients=number_total_clients,
        number_current_impacted=number_current_impacted,
        number_total_impacted=number_total_impacted,
        view=view,
        views=CLIENT_VIEWS,
        entity=entity,
        portfolio=portfolio,
     )
