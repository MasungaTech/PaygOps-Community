from flask import Blueprint

expense = Blueprint('expense', __name__, template_folder='templates')


from . import list_expense, view_expense, edit_expense