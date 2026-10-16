from core_system.role.services import RoleGetterService
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from shared.helpers.select2 import render
from pony.orm.core import rollback
from core_system.users.services.user_getter_service import UserGetterService
from flask.json import jsonify
from core_system.role.models import Role
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.operational_entities.models import OperationalEntity
from pony.orm import db_session, select
from flask import abort, request
from flask_login import login_required, current_user
from core_system.operational_entities.web_app import operational_entities
from stock_management_system.services.stock_count_service import StockCountService
from stock_management_system.stock_status import StockStatus


@operational_entities.route('/<int:entity_id>')
@login_required
@db_session(retry=2)
def view_entity(entity_id):
    entity = OperationalEntitiesGetterService.get_from_user_and_id(current_user.reload(), id=entity_id, strict=True, main_resource=True)
    users = UserGetterService.get_list(current_user.reload())
    used_users = select(uwr.user for uwr in entity.users_with_roles)
    users = users.filter(lambda u: u not in used_users)

    psts = [None] + ProductSubType.select()[:]
    stock_count = [(
        pst,
        StockCountService.get_count(pst, entity, StockStatus.in_stock),
        StockCountService.get_count(pst, entity, StockStatus.with_user),
        StockCountService.get_count(pst, entity, StockStatus.installed)
    ) for pst in psts]

    select2 = {
        'user': {
            'items': users,
            'text': 'full_name'
        },
        'role': {
            'items': Role.select(),
            'text': 'name'
        }
    }

    if entity.is_client_group:
        abort(404)

    return render(
        'view_operational_entities.html', select2=select2,
        entity=entity, stock_count=stock_count
    )
