from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pony.orm import db_session

from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from core_system.users.services.user_getter_service import UserGetterService
from data_system.services.custom_dashboard_service import \
    CustomDashboardService
from shared.helpers.authorizer import authorizer
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService

from . import overview


@overview.route('/custom/<dashboard_name>', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@db_session
def view_custom_dashboard(dashboard_name):
    default_dashboard = CustomDashboardService.get_default_view(dashboard_name)
    if not default_dashboard:
        raise Error('Invalid dashboard name')
    if not CustomDashboardService.should_show_custom_dashboard(dashboard_name):
        flash('You must set up a Dashboard ID to use the custom dashboard. ')
        return redirect(url_for(default_dashboard))
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(
        current_user, request.args, "entity_id", strict=False
    )
    user = UserGetterService.extract_from_user_and_id(
        current_user, request.args, "user_id", strict=False
    )
    iframe_url = CustomDashboardService.get_iframe_url_for_dashboard(
        dashboard_name,
        current_user=current_user,
        entity=entity,
        user=user
    )
    clean_name = CustomDashboardService.get_clean_name_for_dashboard(dashboard_name)
    user_filter = CustomDashboardService.should_show_user_filter(dashboard_name)
    base_url = SettingsService.get_setting('MetabaseURL')
    return render_template(
        'view_custom_dashboard.html',
        clean_name=clean_name,
        dashboard_name=dashboard_name,
        custom_dashboard_iframe_url=iframe_url,
        default_dashboard=default_dashboard,
        base_url=base_url,
        entity=entity,
        user=user,
        users=[(u.id, u.full_name) for u in UserGetterService.get_list(current_user)] if user_filter else [],
        user_filter=user_filter
    )

@overview.route('/custom/generic/<int:dashboard_id>', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@db_session
def view_generic_custom_dashboard(dashboard_id):
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(
        current_user, request.args, "entity_id", strict=False
    )
    user = UserGetterService.extract_from_user_and_id(
        current_user, request.args, "user_id", strict=False
    )
    dashboard_data = request.args.copy()
    dashboard_data['id'] = dashboard_id
    iframe_url = CustomDashboardService.get_iframe_url_for_dashboard(
        dashboard_id,
        current_user=current_user,
        entity=entity,
        user=user,
        dashboard_data=dashboard_data
    )
    clean_name = request.args.get('dashboard_name')
    user_filter = CustomDashboardService.should_show_user_filter(dashboard_id)
    base_url = SettingsService.get_setting('MetabaseURL')
    return render_template(
        'view_custom_dashboard.html',
        clean_name=clean_name,
        dashboard_name=dashboard_id,
        custom_dashboard_iframe_url=iframe_url,
        default_dashboard=None,
        base_url=base_url,
        user=user,
        users=[(u.id, u.full_name) for u in UserGetterService.get_list(current_user)],
        entity=entity,
        user_filter=user_filter
    )
