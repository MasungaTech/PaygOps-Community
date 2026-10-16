from constants import OVERVIEW_VIEWS
import config
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from flask_login import login_required, current_user
from flask import request, render_template, flash, redirect, url_for
from pony.orm import db_session

from shared.helpers.authorizer import authorizer
from shared.services.settings_service import SettingsService
from . import overview
from data_system.patchers import basicStatsBind
from web_app import cache
from flask_caching import make_template_fragment_key
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.core_entities import db
from sales_system.leads.services.lead_getter_service import LeadGetterService
from data_system.services.custom_dashboard_service import CustomDashboardService

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.issue_system.services.issue_service import IssueService
else:
    IssueService = None


class StatsEntity(object):

    def __init__(self, view, entity):
        self.view = view
        self.entity = entity

    def get_clients(self, active=True):
        return ClientGetterService.get_from_filtered_view(current_user.reload(), self.view, self.entity, active=active)

    def getIssueReports(self):
        if not IssueService:
            return []
        return IssueService.get_from_filtered_view(current_user.reload(), self.view, self.entity)

    def get_leads(self):
        return LeadGetterService.get_from_filtered_view(current_user.reload(), self.view, self.entity)

basicStatsBind(StatsEntity)



def get_cache_key_base(view, monthly, entity, user):
    return "overview_html_view-{}_user-{}_entity-{}_monthly-{}_lang-{}".format(view, user.id, entity.id if entity else 'all', monthly, user.person.sms_language or 'EN')
    

def clear_overview_cache(cache_key_base):
    cache_keys = ['_pie_new', '_client_lead_new', '_turnover_service_new', 'turnover_partial_last_new', 'service_partial_last_new']
    for key in cache_keys:
        template_key = make_template_fragment_key(cache_key_base+key)
        cache.delete(template_key)


@overview.route('/', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@db_session
def display_overview():
    replaces_default = CustomDashboardService.replaces_default('overview')
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    view = request.args.get('view', 'all')
    if replaces_default:
        return redirect(url_for('overview.view_custom_dashboard', dashboard_name='overview', view=view, entity_id=entity.id if entity else None))
    else:
        return redirect(url_for('overview.display_overview_default', view=view, entity_id=entity.id if entity else None))



@overview.route('/default_clear_cache', methods=['GET', 'POST'], defaults={'clear_cache': True})
@overview.route('/default', methods=['GET', 'POST'], defaults={'clear_cache': False})
@login_required
@authorizer('ViewClients')
@db_session
def display_overview_default(clear_cache=False):

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    view = request.args.get('view', 'all')

    thisStatEntity = StatsEntity(view, entity)
    monthly = request.args.get('monthly', 0, int)!=0 #('monthly' in request.form)
    cache_key_base = get_cache_key_base(view, monthly, entity, current_user)
    if clear_cache:
        if SettingsService.get_setting('StressMode'):
            flash('We are experiencing a high load on the server. Dashboards have been temporarily disabled.')
        else:
            clear_overview_cache(cache_key_base)
            flash('The stats have been refreshed. ')
            return redirect(url_for('overview.display_overview_default', clear_cache=False, **request.args))
    return render_template("overview.html",
                           thisStatEntity=thisStatEntity,
                           cache_key_base=cache_key_base,
                           view=view,
                           views=OVERVIEW_VIEWS,
                           entity=entity,
                           monthly=monthly)


@overview.route('/welcome', methods=['GET', 'POST'])
@login_required
@db_session
def welcome_overview():
    return render_template(
        'welcome_dashboard.html',
        user=current_user,
    )



