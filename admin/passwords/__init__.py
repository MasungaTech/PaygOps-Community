from flask import Blueprint

auth = Blueprint('login', __name__, template_folder='templates')

from . import login, password_reset
