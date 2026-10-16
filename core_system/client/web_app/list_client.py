from constants import CLIENT_VIEWS
from core_system.client.models import ClientTag
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.helpers.select2 import render
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.client.services.client_tag_getter import ClientTagService
from flask import request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from pony import orm
import config

from core_system.client.services.sorter import ClientSorter
from core_system.client.services.client_list_service import ClientListService
from core_system.client.services.client_getter_service import ClientGetterService
from payg_loan_system.offers.models import OfferType
from shared.helpers.authorizer import authorizer
from shared.helpers.pagination import Pagination
from . import client

if config.ENABLE_ENTERPRISE_FEATURES:
    from task_system.services.task_category_service import TaskCategoryService
    from task_system.services.task_system_service import TaskService


@client.route('/', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@orm.db_session(retry=2)
def list_client():

    pagination = Pagination.generate(request, default_sort='expires_on:asc')
    search = request.args.get('search')

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    client_group = ClientGroupGetterService.extract_from_user_and_id(current_user, request.args, "client_group_id", strict=False)
    status = request.args.get('status', 'all')
    view = request.args.get('view', 'all')

    clients = ClientGetterService.get_from_filtered_view(
        current_user.reload(),
        view=view,
        entity=entity,
        portfolio=portfolio,
        status=status,
        search=search,
        client_group=client_group
    )
    
    tags = request.args.get('tags', '')
    tags = ClientTagService.extract_tags(tags, current_user)
    clients = ClientListService.filter_by_tags(clients, tags)
    if config.ENV_VAR == 'TEST': #workaround till we get rid of mock objects
        clients = clients.filter(lambda c: c.person.village)
    pagination.objects = ClientSorter.sort(clients, pagination.sort)

    valid_statuses = {
        'active_contracts': 'With active contracts (excl. Late Contracts)',
        'defaulted_contracts': 'With defaulted contracts',
        'defaulted_not_repossessed_contracts': 'With contracts pending repossession',
        'cancelled_contracts': 'With cancelled contracts',
        'completed_contracts': 'With completed contracts',
        'overpaid_contracts': 'With overpaid contracts',
        'paused_contracts': 'With paused contracts',
        'active_late_contracts': 'With active or late contracts',
        'active_late_completed_contracts': 'With active, late or completed',
        'late_contracts': 'With late contracts',
        'all': 'All'
    }

    task_category = None

    if config.ENABLE_ENTERPRISE_FEATURES and TaskCategoryService:
        task_category = TaskCategoryService.extract_from_user_and_id(
                            current_user, 
                            request.args, 
                            "name", 
                            strict=False)
    
    users = UserGetterService.get_list(current_user=current_user)
    assignees = TaskService.get_assignees(current_user) if config.ENABLE_ENTERPRISE_FEATURES else []
    contracts = ContractGetterService.get_list(current_user=current_user)
    devices = DeviceGetterService.get_list(current_user=current_user)
    leads = LeadGetterService.get_list(current_user=current_user)
    clients = ClientGetterService.get_list(current_user=current_user)

    select2 = {
        'portfolios': {
            'items': PortfolioGetterService.get_list(current_user),
            'text': 'name',
            'selected': (portfolio.id, portfolio.name) if portfolio else ()
        },
        'client_groups': {
            'items': ClientGroupGetterService.get_list(current_user),
            'text': 'name',
            'selected': (client_group.id, client_group.name) if client_group else ()
        },
        'assignee':{
            'items': assignees,
            'text': 'full_name_and_id',
            'person_search_field': True,
            'force_ajax': True
        } if config.ENABLE_ENTERPRISE_FEATURES else {
            'items': [],
            'text': 'full_name_and_id',
            'person_search_field': True,
            'force_ajax': True
        },
        'task_category_id': {
            'items': TaskCategoryService.get_list(current_user, linked_objects=1) if config.ENABLE_ENTERPRISE_FEATURES and TaskCategoryService else [],
            'text': 'name',
            'selected': task_category,
            'data': {
                    'instructions': 'default_task_instructions',
                    'task_name': 'default_task_name',
                    'linked_objects': 'linked_objects'
            },
        } if config.ENABLE_ENTERPRISE_FEATURES else {
            'items': [],
            'text': 'name',
            'selected': None,
            'data': {}
        },
        'clients': {    
            'items': clients,
            'text': 'full_name_and_id',
            'person_search_field': True
        }
    }

    return render(
        'list_client.html',
        select2=select2,
        pagination=pagination,
        views=CLIENT_VIEWS,
        view=view,
        search=pagination.search,
        status=status,
        valid_statuses=valid_statuses,
        portfolio=portfolio,
        client_group=client_group,
        tags=tags,
        OfferType=OfferType,
        entity=entity,
    )


@client.route('/location/client/<int:client_id>')
@client.route('/location')
@login_required
@authorizer('ViewClients')
@orm.db_session
def clients_map(client_id=None):
    if client_id:
        entity = None
        portfolio = None
        client_group = None
        view = 'all'

        clients = ClientGetterService.get_from_filtered_view(current_user, id=client_id)
        if clients.count():
            clients = clients.filter(lambda c: c.person.GPSLon != None and c.person.GPSLat != None and c.person.GPSLon != config.NaN_VAL and c.person.GPSLat != config.NaN_VAL)
            if not clients.count():
                flash('Client does not have coordinates')
                return redirect(url_for('.list_client'))
        else:
            flash('Client does not exist. ')
            return redirect(url_for('.list_client'))
    else:

        entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
        portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
        client_group = ClientGroupGetterService.extract_from_user_and_id(current_user, request.args, "client_group_id", strict=False)
        view = request.args.get('view', 'all')

        clients = ClientGetterService.get_from_filtered_view(
            current_user.reload(),
            view=view,
            entity=entity,
            portfolio=portfolio,
            client_group=client_group
        )

    clients = clients.filter(lambda c: c.person.GPSLon != None and c.person.GPSLat != None and c.person.GPSLon != config.NaN_VAL and c.person.GPSLat != config.NaN_VAL)
    if clients.count() > 5000:
        flash('Too many clients to show, showing only 5,000.')
        clients = clients.order_by(1).limit(5000)
    elif clients.count() == 0:
        flash('No clients with coordinates to show. ')
        return redirect(url_for('.list_client'))

    return render_template('clients_map.html',
                           Clients=clients,
                           client_id=client_id,
                           entity=entity,
                           view=view,
                           views=CLIENT_VIEWS)
