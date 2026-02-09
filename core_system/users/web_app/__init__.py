from flask import Blueprint

user = Blueprint('user', __name__, template_folder='templates', static_folder='static')

from . import list_users, view_user, edit_user, add_user
