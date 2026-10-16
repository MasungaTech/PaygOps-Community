from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from flask_login import login_required, current_user
from flask import request, flash, redirect, url_for, render_template
from pony.orm import db_session
from shared.logger.loggers import Error
from shared.helpers.authorizer import authorizer
from config import ORGANIZATION_LIST
from core_system.role.methods.getters import get_all_roles
from core_system.users.services.edit_user_service import EditUserService
from shared.helpers.select2 import render
from sales_system.lead_generator.services.lead_generator_type_service import LeadGeneratorTypeService
from . import user


@user.route('/add', methods=["POST"])
@login_required
@authorizer('AddUsers')
@db_session
def create_user():
    try:
        EditUserService.add_from_data_and_user(data=request.form, user=current_user, confirm_password=True)
    except Error as error:
        message = EditUserService.get_human_readable_error(error)
        flash(message)
        return redirect(url_for(".add_user"))
    else:
        flash('User added successfully. ')
        return redirect(url_for('.list_users'))


@user.route('/add', methods=["GET"])
@login_required
@authorizer('AddUsers')
@db_session
def add_user():
    print(request.args)
    shops = OperationalEntitiesGetterService.get_list(current_user, extra_permission="AddUsers", only_hierarchical=True)
    select2 = {
        'role': {
            'items': get_all_roles(True),
            'text': 'name'
        },
        'shops': {
            'items' : OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True),
            'text': 'name'
        }
}
    return render('edit_user.html',
                    select2=select2,
                    ORGANIZATION_LIST=ORGANIZATION_LIST,
                    Shops=shops,
                    lg_types=LeadGeneratorTypeService.get_list(current_user, exclude_default=True))

