from flask import Blueprint

transaction_request = Blueprint('transaction_request', __name__, template_folder='templates')

from . import registration_view, sync_activation_view, give_discount_view, collect_cash_view, swap_device_view, \
    give_delay_view, deregister_view, default_view, undo_default_view, change_offer_view, expected_paid_change_view, cancel_view, \
    pause_view, resume_view, pay_client_view, swap_addon_device_view, assign_addon_device_view
