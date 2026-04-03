from flask import Blueprint

overview = Blueprint('overview', __name__, template_folder='templates')

from . import see_overview, view_custom_dashboard