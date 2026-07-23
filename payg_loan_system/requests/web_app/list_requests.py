from flask import request, render_template
from flask_login import login_required, current_user
from pony.orm import db_session
from constants import CLIENT_VIEWS
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService

from payg_loan_system.requests.models import ActivationRequest, MentorRequest
from payg_loan_system.devices.model.token import Token, TokenSorter
from payg_loan_system.requests.services import ActivationRequestGetter, GetterService, MentorRequestGetter
from shared.helpers.pagination import Pagination
from shared.helpers.authorizer import authorizer
from shared.helpers.list_helpers import timePeriodHelper
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from . import mentor_request


@mentor_request.route('/agent', methods=['GET', 'POST'])
@login_required
@authorizer('ViewActions')
@db_session
def list_request():

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    client_group = ClientGroupGetterService.extract_from_user_and_id(current_user, request.args, "client_group_id", strict=False)
    user = UserGetterService.extract_from_user_and_id(current_user, request.args, "user_id", strict=False)
    device = DeviceGetterService.extract_from_user_and_id(current_user, request.args, "device_id", strict=False)


    view = request.args.get('view', 'all')
    client_id = request.args.get('client_id')

    if view == 'all' and not client_id and current_user.can_access_in_all('ViewClients'):
        clients = None # This is actually needed as passing the full client list makes it slow
    else:
        clients = ClientGetterService.get_from_filtered_view(
            current_user.reload(),
            view=view,
            entity=entity,
            portfolio=portfolio,
            client_group=client_group,
            id=client_id
        )

    time_default = 'forever' if client_id else '14'
    pagination, selected_time = GetterService.filter(
        request,
        MentorRequest,
        'reception_time:desc',
        current_user,
        clients,
        time_default=time_default,
        user=user,
        device=device
    )

    return render_template(
        'user_requests.html',
        pagination=pagination,
        timeFilter=selected_time,
        timeDefault=time_default,
        view=view,
        client_id=client_id,
        views=CLIENT_VIEWS,
        entity=entity
    )


@mentor_request.route('/activation', methods=['GET', 'POST'])
@login_required
@authorizer('ViewActions')
@db_session
def token_list():

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    client_group = ClientGroupGetterService.extract_from_user_and_id(current_user, request.args, "client_group_id", strict=False)
    device = DeviceGetterService.extract_from_user_and_id(current_user, request.args, "device_id", strict=False)
    view = request.args.get('view', 'all')
    client_id = request.args.get('client_id')
    
    if view == 'all' and not client_id and current_user.can_access_in_all('ViewClients'):
        clients = None # This is actually needed as passing the full client list makes it slow
    else:
        clients = ClientGetterService.get_from_filtered_view(
            current_user.reload(),
            view=view,
            entity=entity,
            portfolio=portfolio,
            client_group=client_group,
            id=client_id
        )

    time_default = 'forever' if (client_id or device) else '14'
    selected_time = request.form.get('time_filter', request.args.get('time_filter', time_default))
    params = 'time_filter={}'.format(selected_time)
    limit_time = timePeriodHelper(selected_time, time_default)

    objects = Token.select(lambda t: t.time >= limit_time)
    if device:
        objects = objects.filter(lambda t: t.device == device)
    if clients:
        objects = objects.filter(lambda t: t.device.contract.client in clients)

    pagination = Pagination.generate(request, params)
    pagination.sort = request.args.get('sort', 'time:desc')
    pagination.objects = TokenSorter.sort(objects, pagination.sort)

    return render_template(
        'token_list.html',
        pagination=pagination,
        timeFilter=selected_time,
        timeDefault=time_default,
        view=view,
        client_id=client_id,
        views=CLIENT_VIEWS,
        entity=entity
    )


@mentor_request.route('/agent/<int:request_id>')
@login_required
@authorizer('ViewActions')
@db_session
def view_mentor_requests(request_id):
    return str(MentorRequestGetter.get_from_user_and_id(current_user, request_id, strict=True, main_resource=True).to_dict())


@mentor_request.route('/activation/<int:request_id>')
@login_required
@authorizer('ViewActions')
@db_session
def view_activation_requests(request_id):
    return str(ActivationRequestGetter.get_from_user_and_id(current_user, request_id, strict=True, main_resource=True).to_dict())
