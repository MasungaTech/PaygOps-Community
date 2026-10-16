from flask import Blueprint

phone_numbers = Blueprint('phone_numbers',
                          __name__,
                          template_folder='templates',
                          static_folder='static')

import core_system.phone_numbers.web_app.views
