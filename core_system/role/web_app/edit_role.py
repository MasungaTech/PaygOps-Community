from flask_login import login_required, current_user
from flask import request, render_template, flash
from pony.orm import db_session

from shared.helpers.authorizer import authorizer
from . import permission_system
from core_system.role.models import Permission
from core_system.role.methods.getters import get_role_from_id, get_all_role_types, \
    get_all_role_permissions_code_names, get_permission_objects_from_list_of_names
from core_system.role.methods.setters import edit_role_from_form
from core_system.role.permissions import permission_themes, all_permissions, global_permissions, theme_icons
import json
from core_system.role.services import PermissionService
from shared.logger.loggers import Error, LogAPI
from core_system.role.methods.helpers import permission_spacer

log_api = LogAPI()


@permission_system.route('/role/<int:role_id>')
@login_required
@authorizer('CreateRoles')
@db_session
def edit_role(role_id):
    role_to_edit = get_role_from_id(role_id)
    if not role_to_edit: raise Error('Invalid role id')
    types = get_all_role_types()
    role_permissions = get_all_role_permissions_code_names(role_id)
    return render_template('edit_role.html', 
                            Role_To_Edit=role_to_edit, 
                            permission_themes=permission_themes,
                            theme_icons=theme_icons,
                            all_permissions=all_permissions, Types=types,
                            role_permissions=role_permissions, 
                            permission_spacer=permission_spacer,
                            global_permissions=global_permissions)