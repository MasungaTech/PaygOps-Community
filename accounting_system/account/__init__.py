from flask import Blueprint

account = Blueprint('account', __name__, template_folder='templates', static_folder='static')

from accounting_system.account.views import view_dashboard, reports
