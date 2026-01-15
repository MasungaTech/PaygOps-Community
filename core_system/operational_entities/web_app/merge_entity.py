from flask.helpers import url_for
from pony.orm import db_session
from flask import render_template, abort, request, flash, redirect
from flask_login import login_required, current_user
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.operational_entities.web_app import operational_entities
from core_system.operational_entities.services.operational_entity_merger_service import OperationalEntityMerger
from shared.helpers.authorizer import authorizer
from shared.helpers.select2 import render


@db_session(retry=2)
@operational_entities.route('/<int:entity_id>/merge', methods=['GET', 'POST'])
@login_required
@authorizer('ConfigureOperationalEntitiesAdmin')
@db_session(retry=2)
def merge_entity(entity_id):
    entity = OperationalEntitiesGetterService.get_from_user_and_id(current_user, entity_id, strict=True, main_resource=True)
    if request.method == 'POST':
        from_entity = OperationalEntitiesGetterService.get_from_user_and_id(current_user, request.form.get('from_entity_id'), strict=True)
        OperationalEntityMerger.merge(from_entity, entity)
        flash('Entity merged')
        return redirect(url_for('entities.view_entity', entity_id=entity.id))
    entities_to_merge = OperationalEntitiesGetterService.get_list(current_user, level=entity.level).filter(lambda e: e != entity)

    select2 = {
        'entities': {
            'items': entities_to_merge,
            'text': 'name'
        }
    }
    return render('merge_operational_entities.html',
                    entity=entity, select2=select2)