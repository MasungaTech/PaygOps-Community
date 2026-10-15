from flask import Blueprint

payment = Blueprint('payment', __name__, template_folder='templates', static_folder='static')

from . import add_payment_manually, list_payment, view_payment_account
