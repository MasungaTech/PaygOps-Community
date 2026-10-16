from flask import Blueprint

mentor_request = Blueprint('mentor_request', __name__, template_folder='templates')

from . import direct_request, list_requests
