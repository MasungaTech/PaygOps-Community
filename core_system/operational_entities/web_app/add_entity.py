from munch import Munch
from core_system.users.services.user_getter_service import UserGetterService
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from shared.services.settings_service import SettingsService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.operational_entities.services.edit_operational_entity_service import EditOperationalEntityService
from flask.helpers import url_for
from shared.logger.loggers import Error
from pony.orm import db_session
from flask import render_template, request, abort, flash, redirect, url_for
from flask_login import login_required, current_user
from shared.helpers.authorizer import authorizer
from core_system.operational_entities.web_app import operational_entities


@db_session(retry=2)
@operational_entities.route('/level_<int:level>/add', methods=['GET'])
@login_required
@authorizer(['AddVillages', 'AddClusters', 'AddHubs', 'AddZones', 'AddRegions'])
@db_session(retry=2)
def add_entity(level):

    if not OperationalEntitiesHelper.level_valid(level):
        abort(404)
    
    parents = None
    if level < OperationalEntitiesHelper.get_max_level_enabled():
        parents = {p.id: p.name for p in OperationalEntitiesGetterService.get_list(
            current_user,
            level=level+1
        )}
    
    users = {u.id: u.full_name for u in UserGetterService.get_list(current_user.reload())}

    return render_template('edit_operational_entities.html',
                           parents=parents,
                           level=int(level),
                           users=users,
                           adding=True)
