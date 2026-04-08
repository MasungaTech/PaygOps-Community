from flask import Blueprint

api_system = Blueprint('api_system', __name__, template_folder='templates')

from . import create_token, platform
