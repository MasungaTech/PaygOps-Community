from flask import render_template, request
from flask_login import login_required
from pony.orm import db_session

from core_system.role.methods.getters import get_all_roles
from core_system.role.models import get_role_type_name
from shared.helpers.authorizer import authorizer
from shared.helpers.pagination import Pagination

from . import permission_system


@permission_system.route('/roles', methods=['GET'])
@login_required
@authorizer('ViewRoles')
@db_session
def list_roles():
    roles = get_all_roles(sort=True)
    pagination = Pagination.generate(request)
    pagination.objects = roles
    return render_template(
        'list_roles.html',
        Roles=roles,
        pagination=pagination,
        get_role_type_name=get_role_type_name
    )
