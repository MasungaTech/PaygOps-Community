from flask import Blueprint

sales_dashboard = Blueprint('sales_dashboard', __name__, template_folder='templates')

from . import views
