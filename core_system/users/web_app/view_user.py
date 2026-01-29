from core_system.users.services.operational_permissions_service import OperationalPermissionsService
from pony.orm.core import rollback, flush
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from flask.json import jsonify
from core_system.role.models import Role
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from shared.helpers.select2 import render
from shared.services.settings_service import SettingsService
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWalletType
from flask_login import login_required, current_user
from flask import request, flash, redirect, url_for, abort
from pony.orm import db_session, desc
from core_system.role.services import PermissionService, RoleGetterService

from . import user
from shared.helpers.pagination import Pagination


@user.route('/<int:user_id>')
@login_required
@db_session
def view_user(user_id=None):
    this_user = UserGetterService.get_from_user_and_id(current_user.reload(), user_id, strict=True, main_resource=True)

    clusters_pagination = Pagination.generate(request, tab='clusters')
    clusters_pagination.objects = this_user.managed_operational_entities.filter(lambda oe: oe.level == 1)

    wallets = this_user.payment_wallets.filter(lambda w: w.Type == PaymentWalletType.agent_collection)
    all_cash_payments = Payment.select(lambda p: p.PaymentWallet in wallets).order_by(lambda p: desc(p.PaymentReceptionTime))

    entity_types = {i: SettingsService.get_setting('OperationalEntities')[i]['name'] for i in range(0, OperationalEntitiesHelper.get_max_level_enabled()+1)}
    entity_types[-1] = 'Client Group'
    entity_types_all = entity_types.copy()
    if current_user.can_access_in_all('EditUsers'):
        entity_types_all['all'] = 'All'

    level = request.args.get('level', None)
    entities = OperationalEntitiesGetterService.get_list(current_user, level=level)
    users = UserGetterService.get_list(current_user)
    roles = PermissionService.get_allowed_roles_for_user(current_user)
    select2 = {
        'entities': {
            'items': entities,
            'text': 'name',
            'force_ajax': True
        },
        'roles': {
            'items': roles,
            'text': 'name',
            'force_ajax': True
        },
        'users': {
            'items': users,
            'text': 'full_name'
        }
    }

    return render(
        'view_user.html',
        user=this_user,
        clusters_pagination=clusters_pagination,
        all_cash_payments=all_cash_payments,
        entity_types=entity_types,
        entity_types_all=entity_types_all,
        select2=select2
    )