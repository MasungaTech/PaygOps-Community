from flask import Blueprint

contract = Blueprint('contract', __name__, template_folder='templates')

from . import list_contracts, view_contract, contract_dashboard, addons_list, addon_offers_views, addon_configuration_views
