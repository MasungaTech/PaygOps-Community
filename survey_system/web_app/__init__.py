from flask import Blueprint

survey = Blueprint('survey', __name__, template_folder='templates')
custom_forms = Blueprint('custom_forms', __name__, template_folder='templates')

from survey_system.methods.survey_methods import *

from . import views