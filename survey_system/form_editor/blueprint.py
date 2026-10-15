from flask import Blueprint

forms_blueprint = Blueprint('forms_blueprint', __name__, template_folder='templates', static_folder='static')

from survey_system.form_editor import views
