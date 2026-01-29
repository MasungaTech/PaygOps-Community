from flask import Blueprint

lead_generator = Blueprint('lead_generator', __name__,
                           template_folder='templates',
                           static_folder='static')

from . import add, list, edit, view, chart, merge
