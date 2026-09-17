from flask import Blueprint

administration = Blueprint('admin', __name__, static_folder='static', template_folder='templates')
two_factor = Blueprint('two_factor', __name__)

from admin.web_app import admin, communication_tool_views, device_api_settings, \
    interactions, bulk_upload, menu_testing, settings, two_factor_views
