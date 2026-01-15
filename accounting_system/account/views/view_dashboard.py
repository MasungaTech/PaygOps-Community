from datetime import datetime, timedelta

from flask import render_template, request, get_flashed_messages, redirect, url_for, flash
from flask_login import login_required, current_user
from pony.orm import db_session
from shared.helpers.clock import Clock
from flask_caching import make_template_fragment_key
from shared.helpers.authorizer import authorizer
from accounting_system.account import account

from data_system.services.custom_dashboard_service import CustomDashboardService
from shared.services.settings_service import SettingsService


@account.route('/dashboard', methods=['GET', 'POST'])
@login_required
@authorizer('ViewDashboards')
@db_session
def payments_dashboard():
    replaces_default = CustomDashboardService.replaces_default('accounting')
    if replaces_default:
        return redirect(url_for('overview.view_custom_dashboard', dashboard_name='accounting'))
    else:
        return redirect(url_for('account.payments_dashboard_default'))


@account.route('/dashboard/default', methods=['GET', 'POST'], defaults={'clear_cache': True})
@account.route('/default', methods=['GET', 'POST'], defaults={'clear_cache': False})

@login_required
@authorizer('ViewDashboards')
@db_session
def payments_dashboard_default(clear_cache=False):
    if not current_user.can_access('ViewGlobalDashboards'):
        flash("You don't have the proper authorization level to access this page.")
        return redirect(url_for('index'))

    default_begin_date = datetime.now() + timedelta(days=-365)

    if request.method == 'POST':
        startDate = datetime.strptime(request.form['begin_date'], '%Y-%m-%d')
        finishDate = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        today = datetime.today()
        if today.month+2 <= 12:
            NextMonth = datetime(today.year, today.month+2, 1) - timedelta(days=1)
        else:
            NextMonth = datetime(today.year+1, (today.month+2)-12, 1) - timedelta(days=1) 
        NextMonth = Clock.localize_to_utc(NextMonth, naive=True)
        if startDate >= finishDate or finishDate > NextMonth:
            startDate=default_begin_date
            finishDate=datetime.today()
            flash("The dates are not correct")
    else:
        startDate = default_begin_date
        finishDate = datetime.now()

    if clear_cache:
        if SettingsService.get_setting('StressMode'):
            flash('We are experiencing a high load on the server. Dashboards have been temporarily disabled.')
        else:    
            from web_app import cache
            cache.delete(make_template_fragment_key("lead_stats_data_"+startDate.strftime('%Y-%m-%d')+'_'+finishDate.strftime('%Y-%m-%d')))
            flash('The stats have been refreshed. ')
            return redirect(url_for('account.payments_dashboard_default', clear_cache=False, **request.args))

    return render_template('accounting_dashboard.html',
                        startDate=startDate,
                        finishDate=finishDate,
                        user_key='{}'.format(current_user.id))