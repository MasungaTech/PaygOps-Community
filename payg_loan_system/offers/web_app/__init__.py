from flask import Blueprint

offer_system = Blueprint('offers', __name__, template_folder='templates')

from . import list_offers, view_offer, add_offers, edit_offer
