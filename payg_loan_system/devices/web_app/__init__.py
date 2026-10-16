from flask import Blueprint

device_views = Blueprint('device', __name__, template_folder='templates', static_folder='static')

from munch import Munch

from payg_loan_system.devices.model.token import Token
from payg_loan_system.devices.web_app import delete_device, view_device