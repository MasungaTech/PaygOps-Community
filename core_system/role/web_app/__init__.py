from flask import Blueprint

permission_system = Blueprint('permissions', __name__, template_folder='templates')

from . import create_role, edit_role, list_roles
