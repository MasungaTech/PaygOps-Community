from flask import Blueprint

historical_data = Blueprint('historical_data', __name__,
                            template_folder='templates',
                            static_folder='static')

from .views import charts, dashboard
