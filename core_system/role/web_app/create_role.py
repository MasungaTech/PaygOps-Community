from flask import render_template
from flask_login import login_required
from pony.orm import db_session

from core_system.role.methods.getters import get_all_role_types
from core_system.role.methods.helpers import permission_spacer
from core_system.role.permissions import (all_permissions, global_permissions,
                                          permission_themes, theme_icons)
from shared.helpers.authorizer import authorizer

from . import permission_system


@permission_system.route('/role/add')
@login_required
@authorizer('CreateRoles')
@db_session
def create_role():
    types = get_all_role_types()
    return render_template(
        'edit_role.html',
        permission_themes=permission_themes,
        all_permissions=all_permissions,
        Types=types,
        theme_icons=theme_icons,
        permission_spacer=permission_spacer,
        global_permissions=global_permissions
    )
