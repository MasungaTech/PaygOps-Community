from flask import Blueprint

operational_entities = Blueprint('entities', __name__, template_folder='templates', static_folder='static')

from . import list_entities, add_entity, view_entity, edit_entity, merge_entity, client_group_views
