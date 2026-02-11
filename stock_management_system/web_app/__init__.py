from flask import Blueprint

stock_management = Blueprint('stock', __name__, static_folder='static', template_folder='templates')

from . import views
