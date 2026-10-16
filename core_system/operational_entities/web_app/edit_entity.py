from core_system.users.services.user_getter_service import UserGetterService
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from shared.services.settings_service import SettingsService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.operational_entities.services.edit_operational_entity_service import EditOperationalEntityService
from flask.helpers import url_for
from shared.logger.loggers import Error
from core_system.operational_entities.models import OperationalEntity
from pony.orm import db_session
from flask import render_template, request, abort, flash, redirect, url_for
from flask_login import login_required, current_user
from shared.helpers.authorizer import authorizer
from core_system.operational_entities.web_app import operational_entities


@db_session(retry=2)
@operational_entities.route('/<int:entity_id>/edit', methods=['GET', 'POST'])
@login_required
@authorizer(['EditVillages', 'EditClusters', 'EditHubs', 'EditZones', 'EditRegions'])
@db_session(retry=2)
def edit_entity(entity_id):

    entity = OperationalEntitiesGetterService.get_from_user_and_id(current_user.reload(), id=entity_id)
    if not entity or not current_user.can_access('Edit'+OperationalEntitiesHelper.get_permission_name(entity.level), entity=entity):
        abort(404)
   
    entities_config = SettingsService.get_setting('OperationalEntities')
    parents = None
    if entity.level < 4 and entities_config[entity.level+1].get('enabled', True):
        parents = {p.id: p.name for p in OperationalEntitiesGetterService.get_list(
            current_user,
            level=entity.level+1
        )}
    
    users = {u.id: u.full_name for u in UserGetterService.get_list(current_user.reload())}

    return render_template('edit_operational_entities.html',
                           entity=entity,
                           parents=parents,
                           level=entity.level,
                           users=users,
                           adding=False)