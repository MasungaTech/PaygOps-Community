from flask import Blueprint

portfolios = Blueprint(
    'portfolios',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import views