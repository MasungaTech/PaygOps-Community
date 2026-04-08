from core_system.role.models import ROLE_TYPE_NAMES
from constants import USER_VIEWS
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.role.services import RoleGetterService
from core_system.users.services.sorter import UserSorter
from core_system.users.services.user_getter_service import UserGetterService
from flask_login import login_required, current_user
from flask import render_template, request
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from shared.helpers.pagination import Pagination
from shared.helpers.select2 import render
from . import user


@user.route('/', strict_slashes=False, methods=['GET', 'POST'])
@login_required
@authorizer('ViewUsers')
@db_session
def list_users():

    search = request.args.get('search', '')
    active_filter = request.args.get('active_filter', 'default')
    role_type = request.args.get('role_type', '')
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    role = RoleGetterService.extract_from_user_and_id(current_user, request.args, "role", strict=False)
    view = request.args.get('view', 'all')

    users = UserGetterService.get_from_filtered_view(
        current_user.reload(),
        view=view,
        entity=entity,
        search=search,
        active=active_filter,
        role_type=role_type,
        role=role
    )

    select2 = {
        'roles': {    
            'items': RoleGetterService.get_list(current_user),
            'selected': role,
            'text': 'name',
        },
    }

    pagination = Pagination.generate(request)
    pagination.objects = UserSorter.sort(users, pagination.sort)

    return render(
        'list_users.html',
        select2=select2,
        pagination=pagination,
        search=search,
        active_filter=active_filter,
        view=view,
        views=USER_VIEWS,
        entity=entity,
        role_type=role_type,
        role=role,
        role_types=ROLE_TYPE_NAMES,
        active_options={
            'all': 'All users',
            'default': 'Only active users',
            'inactive': 'Only inactive users'
        }
    )
