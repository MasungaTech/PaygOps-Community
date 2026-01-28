from flask import flash, render_template, redirect, url_for, \
    request
from flask_login import current_user, login_required
from pony.orm import db_session
from datetime import timedelta, datetime
from data_system.old_system.stats import StatsEngine
from data_system.old_system.stats_helper import StatsHelper
from shared.helpers.authorizer import authorizer
from shared.helpers.clock import Clock
from flask_caching import make_template_fragment_key
from shared.services.settings_service import SettingsService
from . import sales_dashboard

from data_system.services.custom_dashboard_service import CustomDashboardService

Stats = StatsEngine()
Stats_Helper = StatsHelper()


@sales_dashboard.route('/', methods=['GET', 'POST'])
@login_required
@authorizer('ViewDashboards')
@db_session
def sales_dashboard_view():
    replaces_default = CustomDashboardService.replaces_default('sales')
    if replaces_default:
        return redirect(url_for('overview.view_custom_dashboard', dashboard_name='sales'))
    else:
        return redirect(url_for('sales_dashboard.sales_dashboard_default'))


@db_session(retry=2)
@sales_dashboard.route('/default_clear_cache', methods=['GET', 'POST'], defaults={'clear_cache': True})
@sales_dashboard.route('/default', methods=['GET', 'POST'], defaults={'clear_cache': False})
@login_required
@authorizer('ViewDashboards')
@db_session(retry=2)
def sales_dashboard_default(clear_cache=False):

    if not current_user.can_access('ViewGlobalDashboards'):
        flash("You don't have the proper authorization level to access this page.")
        return redirect(url_for('index'))

    begin_date = datetime.now() + timedelta(days=-365)

    if request.method == 'POST':
        BeginDate = datetime.strptime(request.form['begin_date'], '%Y-%m-%d')
        EndDate = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        today = datetime.today()
        if today.month+2 <= 12:
            NextMonth = datetime(today.year, today.month+2, 1) - timedelta(days=1)
        else:
            NextMonth = datetime(today.year+1, (today.month+2)-12, 1) - timedelta(days=1) # to account for year shift
        NextMonth = Clock.localize_to_utc(NextMonth, naive=True)
        if BeginDate >= EndDate or EndDate > NextMonth:
            BeginDate=begin_date
            EndDate=datetime.today()
            flash("The dates are not correct")
    else:
        BeginDate = begin_date
        EndDate = datetime.now()

    if clear_cache:
        if SettingsService.get_setting('StressMode'):
            flash('We are experiencing a high load on the server. Dashboards have been temporarily disabled.')
        else:    
            from web_app import cache
            cache.delete(make_template_fragment_key("lead_stats_data_"+BeginDate.strftime('%Y-%m-%d')+'_'+EndDate.strftime('%Y-%m-%d')))
            flash('The stats have been refreshed. ')
            return redirect(url_for('sales_dashboard.sales_dashboard_default', clear_cache=False, **request.args))

    return render_template('dashboard_sales.html',
                           Stats=Stats,
                           StatsHelper=Stats_Helper,
                           BeginDate=BeginDate,
                           EndDate=EndDate)
