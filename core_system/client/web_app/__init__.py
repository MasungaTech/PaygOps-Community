from flask import Blueprint
from shared.helpers.log_helper import Logger

logger = Logger.get_logger()
client = Blueprint('client', __name__,
                   template_folder='templates',
                   static_folder='static')

from . import list_client, view_client, edit_client, client_demographics_dashboard, merge_clients
