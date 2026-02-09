from flask import Blueprint

leads = Blueprint('leads', __name__, template_folder='templates', static_folder="static")

from . import add_lead, view_lead, edit_lead, list_lead
