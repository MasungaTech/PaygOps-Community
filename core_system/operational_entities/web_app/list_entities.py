from shared.helpers.select2 import render
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from core_system.operational_entities.services.operational_entities_sorter import OperationalEntitySorter
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from shared.helpers.pagination import Pagination
from core_system.operational_entities.models import OperationalEntity
from pony.orm import db_session
from flask import render_template, abort, request
from flask_login import login_required, current_user
from shared.helpers.authorizer import authorizer
from core_system.operational_entities.web_app import operational_entities


@operational_entities.route('/select_data/<string:level>', methods=['GET'])
@login_required
@db_session(retry=2)
def list_entities_for_select(level):
    if not OperationalEntitiesHelper.level_name_valid(level) or OperationalEntitiesHelper.get_level(level) > OperationalEntitiesHelper.get_max_level_enabled():
        abort(404)
    parent = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, 'parent_id')
    if request.args.get('excluded') not in ['None', None] and not request.args.get('parent_id'):
        parent = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, 'excluded').parent
        
    entities = OperationalEntitiesGetterService.get_list(current_user, level_name=level, parent=parent)
    select2 = {
        'entity': {
            'items': entities,
            'text': 'name'
        },
    }

    return render(select2=select2)


@operational_entities.route('/level_<int:level>', methods=['GET', 'POST'])
@login_required
@db_session(retry=2)
def list_entities(level):

    if not OperationalEntitiesHelper.level_valid(level) or level > OperationalEntitiesHelper.get_max_level_enabled():
        abort(404)

    parent_id = request.args.get('parent') or None
    parent = None
    if parent_id:
        parent = OperationalEntitiesGetterService.get_from_user_and_id(current_user, parent_id)

    pagination = Pagination.generate(request)
    entities = OperationalEntitiesGetterService.get_list(current_user=current_user, level=level, parent=parent)
    if pagination.search:
        
        entities = entities.filter(lambda e: pagination.search.lower() in f'{e.name.lower()} {e.id}')
    pagination.objects = OperationalEntitySorter.sort(entities, pagination.sort)

    return render_template('list_operational_entities.html',
                           pagination=pagination,
                           level=level,
                           parent=parent)