from flask import Blueprint

file_exporter = Blueprint('files', __name__, template_folder='templates')

from data_system.csv_exports.web_app import views
