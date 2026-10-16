from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from flask_login import login_required, current_user
from flask import request, flash, redirect, url_for, \
    render_template, abort
from pony.orm import db_session
from core_system.users.services.user_getter_service import UserGetterService
from shared.helpers.authorizer import authorizer
from config import ORGANIZATION_LIST
from core_system.users.models.user_model import User
from core_system.role.methods.getters import get_all_roles
from core_system.users.services.edit_user_service import EditUserService
from shared.logger.loggers import Error
from sales_system.lead_generator.services.lead_generator_type_service import LeadGeneratorTypeService
from . import user
from shared.helpers.select2 import render
from shared.services.two_factor_service import TwoFactorService


@user.route('/<int:user_id>/edit', methods=['GET'])
@login_required
@authorizer('EditUsers', '.list_users')
@db_session
def edit_user(user_id):
    this_user = UserGetterService.get_from_user_and_id(current_user, user_id, strict=True, main_resource=True)
    shops = OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True)
    roles = get_all_roles(True)
    select2 = {
        'role': {
            'items': roles,
            'selected': this_user.AuthorizationLevel,
            'text': 'name'
        },
        'shops': {
            'items' : shops,
            'selected': this_user.shop,
            'text': 'name'
        }
    }
    return render(
        'edit_user.html',
        User=this_user,
        ORGANIZATION_LIST=ORGANIZATION_LIST,
        select2=select2,
        lg_types=LeadGeneratorTypeService.get_list(current_user, exclude_default=True))


@user.route('/<int:user_id>/edit', methods=['POST'])
@login_required
@authorizer('EditUsers', '.list_users')
@db_session
def update_user(user_id):
    this_user = UserGetterService.get_from_user_and_id(current_user, user_id, strict=True, main_resource=True)
    try:
        EditUserService.edit_from_data_and_user(
            this_user,
            request.form,
            current_user,
            confirm_password=True,
        )
    except Error as error:
        message = EditUserService.get_human_readable_error(error)
        flash(message)
        return redirect(url_for(".edit_user", user_id=user_id))
    else:
        flash('User edited successfully. ')
        return redirect(url_for('.view_user', user_id=this_user.id))


@user.route('/<int:user_id>/two_factor/reset', methods=['POST'])
@login_required
@authorizer('EditUsers', '.list_users')
@db_session
def reset_two_factor(user_id):
    from core_system.role.services import PermissionService
    this_user = UserGetterService.get_from_user_and_id(current_user, user_id, strict=True, main_resource=True)
    if not PermissionService.allowed_to_change_to_role(current_user, this_user.AuthorizationLevel):
        flash('You do not have permission to reset two-factor authentication for this user.')
    else:
        TwoFactorService.disable_2fa_for_user(this_user)
        flash('Two-factor authentication has been disabled/reset for this user.')
    return redirect(url_for('.edit_user', user_id=this_user.id))
