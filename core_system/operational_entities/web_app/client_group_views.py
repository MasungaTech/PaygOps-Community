from core_system.role.services import RoleGetterService
from shared.helpers.select2 import render
from core_system.role.models import Role
from flask.json import jsonify
from core_system.users.services.user_getter_service import UserGetterService
from core_system.operational_entities.services.client_group_sorter import ClientGroupSorter
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from shared.helpers.pagination import Pagination
from pony.orm import db_session, rollback, select
from flask_login import login_required, current_user
from shared.helpers.authorizer import authorizer
from core_system.operational_entities.web_app import operational_entities
from flask import render_template, request, abort


@operational_entities.route('/client_groups', methods=['GET', 'POST'])
@login_required
@db_session
def list_client_groups():

    pagination = Pagination.generate(request)
    groups = ClientGroupGetterService.get_list(current_user)
    if pagination.search:
        groups = groups.filter(lambda g: pagination.search.lower() in f'{g.name.lower()} {g.id}')
    pagination.objects = ClientGroupSorter.sort(groups, pagination.sort)

    return render_template('list_client_groups.html',
                           pagination=pagination)


@operational_entities.route('/client_groups/<int:id>', methods=['GET'])
@login_required
@authorizer(['EditClientGroups'])
@db_session
def edit_client_groups(id):

    client_group = ClientGroupGetterService.get_from_user_and_id(current_user, id, strict=True, main_resource=True)
    
    users = UserGetterService.get_list(current_user.reload())
    managers = {u.id: u.full_name for u in users}

    used_users = select(uwr.user for uwr in client_group.users_with_roles)
    associated_users = users.filter(lambda u: u not in used_users)

    select2 = {
        'user': {
            'items': associated_users,
            'text': 'full_name'
        },
        'role': {
            'items': Role.select(),
            'text': 'name'
        }
    }

    return render('edit_client_group.html', select2=select2,
                           client_group=client_group,
                           users=managers)

@operational_entities.route('/client_groups/add', methods=['GET'])
@login_required
@authorizer(['AddClientGroups'])
@db_session
def add_client_group():

    users = {u.id: u.full_name for u in UserGetterService.get_list(current_user.reload())}

    return render_template('edit_client_group.html',
                           users=users)