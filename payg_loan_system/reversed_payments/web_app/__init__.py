from flask import Blueprint

reversed_payment = Blueprint('reversed_payment', __name__,
                             template_folder='templates',
                             static_folder='static')

from . import views
