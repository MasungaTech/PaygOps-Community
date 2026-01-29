from typing import Literal
from core_system.role.methods.helpers import permission_spacer
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from core_system.client.services.client_tag_getter import ClientTagService
from flask import url_for, render_template, flash, redirect
from markdown import markdown
import json
from payg_loan_system.devices.services.device_tag_getter import DeviceTagService
from shared.api_helpers.client_helpers.json_datetime_helpers import json_serializer
from shared.services.web_menu_service import WebMenuService
import time
from datetime import date
from math import log10, floor
import re
from flask import request, g
from flask_login import current_user
from munch import DefaultMunch
from pony.orm import *
from jinja2 import pass_context
import markupsafe
import flask
from core_system.users.models.user_model import User

import config

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.issue_system.services.issue_service import IssueService
    from task_system.services.task_system_service import TaskService
from accounting_system.accounting_interface import getAllTransferRequests, TransferStatus
from shared.helpers.time_helpers import *
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.lead import Lead
from stock_management_system.services.product_sub_type_service import ProductSubTypeService
from stock_management_system.stock_status import StockStatus
from survey_system.models.question_type import QuestionType
from survey_system.models.languages import Languages
from core_system.core_entities import db
from payg_loan_system.contracts.services.addon_list_service import AddonListService
from web_app import app
from shared.logger.loggers import LogService, RotatingFile
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt_for_user
from datetime import datetime
import uuid
from shared.helpers.clock import Clock
from shared.services.settings_service import SettingsService, Settings
from shared.services.language_service import LanguageService
from shared.services.access_log_service import AccessLogService
from shared.cache.redis_config import get_cache_key, set_cache_key
from messages_system.services.notifications_service import NotificationsService
from constants import HIDE_CHROME_CHECKER_COOKIE_NAME, HIDE_CHROME_CHECKER_COOKIE_MAX_AGE, MAX_ENTITY_LEVEL
from shared.services.audit_log_service import AuditLogService


@app.context_processor
def check_browser():
    browser = request.user_agent.browser
    hide_chrome_checker_cookie = request.cookies.get(HIDE_CHROME_CHECKER_COOKIE_NAME)
    show_chrome_checker = (browser != 'chrome' and hide_chrome_checker_cookie != "True")
    is_custom_app = config.check_if_custom_app(request)
    return dict(show_chrome_checker_modal=show_chrome_checker,
                HIDE_CHROME_CHECKER_COOKIE_NAME=HIDE_CHROME_CHECKER_COOKIE_NAME,
                HIDE_CHROME_CHECKER_COOKIE_MAX_AGE=HIDE_CHROME_CHECKER_COOKIE_MAX_AGE,
                is_custom_app=is_custom_app)


@app.context_processor
def cookie_processor():
    return dict(get_cookie=request.cookies.get)


@app.before_request
def pageload_timer():
    g.request_start_time = time.time()
    g.request_time = lambda: "%.5fs" % (time.time() - g.request_start_time)


@app.after_request
def set_headers(response):
    # Allow iframe embedding only from localhost
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' capacitor://* file://* ionic://* http://localhost http://localhost:8100"
    response.headers.pop('X-Frame-Options', None)  # Remove default X-Frame-Options
    return response


@app.after_request
def pageload_timer_alert(response):
    if 'file/export' in str(request.url_rule):
        return response  # We exclude the files as they might take long to download
    load_time = (time.time() - g.request_start_time)
    if load_time > config.PAGELOAD_WARNING_THRESHOLD:
        LogService.Warning(f"Page load took [{load_time:.1f}] seconds")
    return response


@app.before_request
@db_session
def user_log():
    if not any(re.match(regex, request.path) for regex in config.NOT_LOGGED_PATHS):
        try:
            if current_user.is_authenticated:
                current_user.update_last_web_connection()
                x = current_user.full_name # DO NOT REMOVE THIS IS A WEIRD FIX
                x = current_user.AuthorizationLevel.name # DO NOT REMOVE THIS IS A WEIRD FIX
                AccessLogService.insert(request, 'web_app', current_user.id)
        except Exception as error:
            print('Unkown error while logging access: '+repr(error))


@app.before_request
@db_session
def enforce_two_factor_when_required():
    # Allowlist endpoints and paths to avoid redirect loops
    endpoint = request.endpoint or ''
    if any(re.match(regex, request.path) for regex in config.NOT_LOGGED_PATHS) or endpoint.startswith('two_factor.'):
        return
    # Only enforce on authenticated users and when setting is enabled
    try:
        if not current_user.is_authenticated:
            return
        if not get_global_setting('enforceTwoFactorForAllUsers'):
            return
        # If user already has 2FA, nothing to do
        if getattr(current_user, 'two_factor_enabled', False):
            return
        # Redirect user to 2FA setup
        flash('Your administrator requires two-factor authentication. Please enable 2FA to continue.', 'warning')
        return redirect(url_for('two_factor.setup_2fa'))
    except Exception as error:
        # Fail-open to avoid blocking access if something goes wrong
        print('Error during 2FA enforcement: '+repr(error))
        return


@app.context_processor
def country_processor():
    return dict(Currency=get_global_setting('CurrencySymbol'), CountryName=get_global_setting('CountryName'), CountryDescriptor=get_global_setting('CountryDescriptor'),
                PhoneExtension=get_global_setting('PhoneExtension'), PhoneLength=get_global_setting('PhoneLength'), PhoneLengthMin=get_global_setting('PhoneLengthMin'))


@app.context_processor
def datetime_processor():
    return dict(NOW=datetime.now(), min_date=datetime.min, FirstOfTheYear=date(date.today().year, 1, 1), timedelta=timedelta)


@app.context_processor
def enums():
    return {
        'StockStatus': StockStatus
    }


@app.context_processor
def app_version():
    return dict(VERSION=config.VERSION, COMMIT_SHA=config.COMMIT_SHA, ASSETS_HASHES=app.config['webassets_hashes'])


@app.context_processor
def EmptyObject_processor():
    return dict(EmptyObject=DefaultMunch(None, {}))


@app.context_processor
def config_processor():
    config.SMS_VARIABLES_INFO['custom_id']['name'] = get_global_setting('CustomId')
    config.SMS_VARIABLES_INFO['custom_id']['description'] = config.SMS_VARIABLES_INFO['custom_id']['description'].replace('%CustomIDName%', get_global_setting('CustomId'))
    config.SMS_VARIABLES_INFO['currency_sym']['example'] = get_global_setting('CurrencySymbol')
    return dict(config=config)


def any_filter(filters=[]):
    any_filters = False
    for filter in filters:
        if filter and filter not in ['all', 'default']:
            any_filters = True
    return any_filters


@app.context_processor
def helpers_processor():
    return dict(getWeekDate=getWeekDate, getMonthDate=getMonthDate, any_filter=any_filter)

@app.context_processor
def repayment_types_processor():
    return dict(ContractRepaymentDiscountTypes=ContractRepaymentDiscountTypes)


@app.context_processor
def api_context_processor():
    this_uuid = str(uuid.uuid1())

    if current_user.is_authenticated:
        this_token = current_user.get_api_key()
    else:
        this_token = ""

    return dict(jwt_token=this_token,
                this_uuid=this_uuid,
                payg_api_url=config.PAYG_API_URL)


icons = {}
icons['filter'] = 'filter_list'
icons['district'] = 'map'
icons['api'] = 'api'
icons['village'] = 'home'
icons['home'] = 'home'
icons['client'] = 'account_circle'
icons['lead'] = 'gps_fixed'
icons['mentor'] = 'people_outline'
icons['GPS'] = 'room'
icons['map'] = 'map'
icons['phone'] = 'call'
icons['contact_phone'] = 'ring_volume'
icons['village_chief'] = 'person'
icons['population'] = 'people'
icons['grid'] = 'location_city'
icons['business'] = 'store'
icons['price'] = 'monetization_on'
icons['edit'] = 'mode_edit'
icons['merge'] = 'call_merge'
icons['save'] = 'save'
icons['device'] = 'payment'
icons['battery'] = 'battery_charging_full'
icons['panel'] = 'grid_on'
icons['date'] = 'event'
icons['activity_log'] = 'event_note'
icons['tasks'] = 'assignment_turned_in'
icons['data'] = 'timeline'
icons['info'] = 'info'
icons['time'] = 'av_timer'
icons['offer'] = 'add_shopping_cart'
icons['addon_offer'] = 'add_to_queue'
icons['bundle'] = 'deployed_code'
icons['category'] = 'category'
icons['addon'] = 'queue'
icons['mode'] = 'tonality'
icons['amount'] = 'attach_money'
icons['expense'] = 'receipt'
icons['receipt'] = 'receipt'
icons['description'] = 'description'
icons['user'] = 'account_box'
icons['download'] = 'archive'
icons['transfer'] = 'redo'
icons['account'] = 'account_balance'
icons['delete'] = 'delete'
icons['report'] = 'assignment'
icons['request'] = 'archive'
icons['activation_request'] = 'power_settings_new'
icons['weather'] = 'wb_cloudy'
icons['warning'] = 'warning'
icons['fuel'] = 'local_gas_station'
icons['mileage'] = 'motorcycle'
icons['department'] = 'widgets'
icons['status'] = 'assignment_turned_in'
icons['decision'] = 'gavel'
icons['issue'] = 'error'
icons['interaction'] = 'record_voice_over'
icons['missed_interaction'] = 'timer_off'
icons['graph_up'] = 'trending_up'
icons['graph_pie'] = 'pie_chart'
icons['prospect'] = 'flash_on'
icons['generator'] = 'volume_up'
icons['expire'] = 'alarm'
icons['progression'] = 'trending_up'
icons['activation_ratio'] = 'slow_motion_video'
icons['notes'] = 'textsms'
icons['info_tooltip'] = 'info_outline'
icons['accounting'] = 'monetization_on'
icons['payment'] = 'monetization_on'
icons['reconciliation'] = 'alt_route'
icons['cash'] = 'local_atm'
icons['add_circle'] = 'add_circle_outline'
icons['remove'] = 'remove_circle_outline'
icons['team'] = 'people'
icons['shop'] = 'store'
icons['cluster'] = 'filter_tilt_shift'
icons['management'] = 'supervisor_account'
icons['view'] = 'visibility'
icons['allowed'] = 'verified_user'
icons['forbidden'] = 'remove_circle'
icons['permission'] = 'pan_tool'
icons['message'] = 'chat'
icons['service'] = 'support_agent'
icons['orphaned'] = 'help_outline'
icons['mobile_money'] = 'phone_android'
icons['all'] = 'all_out'
icons['new'] = 'new_releases'
icons['stats'] = 'insert_chart'
icons['old'] = 'update'
icons['priority'] = 'report'
icons['status'] = 'check_circle'
icons['planning'] = 'date_range'
icons['method'] = 'contact_phone'
icons['mobile'] = 'phone_android'
icons['admin'] = 'settings_applications'
icons['admin_specific'] = 'admin_panel_settings'
icons['settings'] = 'settings'
icons['logout'] = 'exit_to_app'
icons['expand'] = 'expand_more'
icons['search'] = 'search'
icons['tags'] = 'style'
icons['task'] = 'task_alt'
icons['special'] = 'extension'
icons['sync'] = 'cached'
icons['reversal'] = 'replay'
icons['mobile_phone'] = 'stay_current_portrait'
icons['user_manual'] = 'help'
icons['key'] = 'vpn_key'
icons['question_answer'] = 'contact_support'
icons['birthdate'] = 'insert_invitation'
icons['forms'] = 'assignment_add'
icons['portfolios'] = 'work'
icons['import_export'] = 'import_export'
icons['import'] = 'play_for_work'
icons['data_export'] = 'file_copy'
icons['analytical_db'] = 'table_view'
icons['hierarchy'] = 'line_style'
icons['contract'] = 'description'
icons['wallet'] = 'account_balance_wallet'
icons['days_late'] = 'av_timer'
icons['add_on'] = 'queue'
icons['desktop'] = 'desktop_windows'
icons['payment_router'] = 'device_hub'
icons['inventory'] = 'local_shipping'
icons['stock'] = 'dns'
icons['communication'] = 'tap_and_play'
icons['sales'] = 'gps_fixed'
icons['more'] = 'more_vert'
icons['more_tag'] = 'more'
icons['move_entities_up'] = 'dynamic_feed'
icons['billing'] = 'receipt_long'
icons['premium'] = 'verified'
icons['token'] = 'pin'
icons['process'] = 'rebase_edit'
icons['process_step'] = 'steppers'


@app.context_processor
def icons_processor():
    return dict(icons=icons)


def get_notifications(theme):
    CACHE_THRESHOLD = 1000
    if not current_user.is_authenticated:
        return None
    permission_all = None
    if theme == 'issues':
        if not config.ENABLE_ENTERPRISE_FEATURES or not IssueService:
            return None
        permission = 'ViewBadgeIssues'
        items = IssueService.get_list(current_user, open=True)
    elif theme == 'leads':
        permission = 'ViewBadgeLeads'
        items = select(L for L in Lead if L.awaiting_decision)
    elif theme == 'transfers':
        permission = 'ViewBadgeTransfers'
        items = getAllTransferRequests().filter(lambda T: T.status == TransferStatus.awaitingDecision)
    elif theme == 'addons':
        permission = 'ViewBadgeTransfers'
        # We disable this for now as it's very slow and not used
        # items = AddonListService.get_list(current_user, status="pending").filter(lambda a: a.not_lead)
        items = None
    elif theme == 'notifications':
        permission = 'SeeHubNotificationsAdmin'
        permission_all = 'SeeAllNotificationsAdmin'
        items = NotificationsService.get_list(current_user, unseen=True)
    elif theme == 'tasks':
        if not config.ENABLE_ENTERPRISE_FEATURES:
            return None
        items = TaskService.get_count_not_completed_nor_cancelled(current_user)
        return items # We don't want to cache this as it's fairly low volume and live
    else:
        return None
    all = False
    if permission_all and current_user.can_access(permission_all):
        all = True
    if all or current_user.can_access(permission):
        if all:
            cache_key = theme+'_notif'
        else:
            cache_key = theme+'_user_'+str(current_user.id)+'_notif'
        count = get_cache_key(cache_key)
        if not count:
            count = items.count() if hasattr(items, 'count') else None
            if count and count > CACHE_THRESHOLD:
                set_cache_key(cache_key, count, 5*60)
        return count
    else:
        return None


@app.context_processor
@db_session
def notification_processor():
    return {'get_notifications': get_notifications}


@app.context_processor
def entity_type_processor():
    return dict(QuestionType=QuestionType, Languages=Languages)


def round_sig(x, sig=2):
    return round(x, sig - int(floor(log10(x))) - 1)


def humanize_number(value, fraction_point=1):
    if value == 0:
        return 0
    powers = [10 ** x for x in (12, 9, 6, 3, 0)]
    human_powers = ('t', 'b', 'm', 'k', '')
    is_negative = False
    if not isinstance(value, float):
        value = float(value)
    if value < 0:
        is_negative = True
        value = abs(value)
    return_value = str(value)
    for i, p in enumerate(powers):
        if value >= p:
            return_value = str(round_sig(value / p, fraction_point)) + human_powers[i]
            break
    if is_negative:
        return_value = "-" + return_value
    return return_value


def simple_human_number(num):
    if num is None:
        return ''
    num = float('{:.3g}'.format(float(num)))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


def pretty_number(value):
    return format(int(value), ',d')


@app.context_processor
def humanizer_processor():
    return dict(humanize_number=humanize_number, human_number=simple_human_number, pretty_number=pretty_number)


def get_setting_from_cache(key):
    if not request.environ.get('settings_cache'):
        settings_cache = {}
        for setting in Settings.select()[:]:
            settings_cache[setting.key] = setting
        request.environ['settings_cache'] = settings_cache
    setting = request.environ['settings_cache'].get(key)
    return SettingsService.get_setting(key=key, setting=setting)


def get_global_setting(key):
    return get_setting_from_cache(key)
    #return SettingsService.get_setting(key)


@app.context_processor
def settings_processor():
    return dict(GlobalSetting=get_global_setting)

@app.context_processor
def device_type_subtype_mapping_processor():
    psts = ProductSubTypeService.get_list(current_user)
    return dict(device_type_subtype_mapping={
        pst.id: pst.device_type for pst in psts
    })

@app.context_processor
def uuid_generator():
    return dict(generate_uuid=uuid.uuid1)


@app.context_processor
def sms_languages_processor():
    return dict(
        CLIENT_SMS_LANGUAGES=LanguageService.get_client_sms_language_dict(),
        USERS_SMS_LANGUAGES=LanguageService.get_user_sms_language_dict()
    )


@app.context_processor
def global_shop_name():
    operational_entities_config = get_global_setting('OperationalEntities')
    return dict(
        OperationalEntitiesHelper=OperationalEntitiesHelper,
        OPERATIONAL_ENTITIES_CONFIG=operational_entities_config
    )


@app.context_processor
def generic_variables():
    platform_type = SettingsService.get_setting('PlatformType')
    return dict(platform_type=platform_type, WEB_MENU_INFO=WebMenuService.get_menu(current_user) if current_user.is_authenticated else None, test_mode=config.is_dev_mode(), reload_templates=config.reload_templates)


@app.context_processor
def page_is_tracked():
    if config.TRACK_ALL:
        return dict(page_is_tracked=True)
    for t in config.TRACKED_ENDPOINTS:
        if request.url_rule.endpoint.startswith(t):
            return dict(page_is_tracked=True)
    return dict(page_is_tracked=False)


def multi_input_name(name, multiple=False, index=0):
    if multiple:
        if ':skip' in name:
            return name.replace(':skip', '')+'['+str(index)+']:skip'
        return name+'['+str(index)+']'
    return name

def person_data_required(key, data=None):
    if key == 'custom_id':
        visible = get_global_setting('CustomIdEnabled')
        if not visible:
            return False
        required = get_global_setting('CustomIdMandatory')
    else:
        required = get_global_setting('LeadInfoSettings').get(key, {}).get('required', False)
    if not required and data:
        required = data.get(key, {}).get('required', False)
    return required

def person_data_visible(key, data=None, edit=False):
    ALWAYS_REQUIRED_FOR_CREATION = ['l0_entity_id']
    if data:
        visible = data.get(key, {}).get('visible', False)
    else:
        if 'l0_entity_id' in key:
            return True
        if key == 'custom_id':
            visible = get_global_setting('CustomIdEnabled')
        else:   
            visible = get_global_setting('LeadInfoSettings').get(key, {}).get('visible', False)
    if not edit and not visible:
        if key in ALWAYS_REQUIRED_FOR_CREATION:
            return True
        return person_data_required(key, data)
    return visible

@app.context_processor
def helper_function_processor():
    return dict(
        datetime_localizer=Clock.localize, 
            multi_input_name=multi_input_name, 
        person_data_required=person_data_required,
        person_data_visible=person_data_visible
    )

BREADCRUMBS_CONFIG = {
    'clients': {'list': 'client.list_client', 'view': 'simple'},
    'contracts': {'list': 'contract.list_contracts', 'view': 'simple'},
    'leads': {'list': 'leads.list_lead', 'view': 'simple'},
    'lead_generators': {'list': 'lead_generator.list_lead_generator', 'view': 'simple'},
    'interactions': {'list': 'interaction_report.list_interaction_report', 'view': 'simple'},
    'issues': {'list': 'issue.list_issue', 'view': 'simple'},
    'stock_items': {'list': 'stock.stock_list', 'view': 'simple'},
    'stock_movements': {'list': 'stock.stock_movements', 'view': 'simple'},
    'stock_count': {'list': 'stock.stock_count', 'view': 'simple'},
    'add-ons': {'list': 'contract.list_addons', 'view': 'simple'},
    'admin': {'list': 'admin.admin'},
    'forms': {'list': 'forms_blueprint.list_forms', 'view': 'simple', 'parent': 'settings'},
    'settings': {'list': 'admin.settings_menu'},
    'journeys': {'list': 'user_journey_editor.journeys_big_menu'},
    'journey_run': {'list': 'user_journey_editor.journeys_big_menu'},
    'user_journeys': {'list': 'user_journey_editor.list_journeys'},
    'mobile_app_customization_card': {'list': 'user_journey_editor.mobile_app_customization_card'},
    'overview': {'list': 'overview.display_overview'},
    'dashboards': {'list': 'overview.display_overview'},
    'communication_campaigns': {'list': 'admin.communication_campaigns', 'parent': 'admin'},
    'expenses': {'list': 'expense.list_expense', 'view': 'simple'},
    'payment_reversals': {'list': 'reversed_payment.list_all', 'view': 'simple'},
    'payments': {'list': 'payment.list_payment', 'view': 'simple'},
    'payment_wallets': {'list': 'payment.list_payment', 'view': 'simple'},
    'cash_collection_wallets': {'list': 'payment.list_payment', 'view': 'simple'},
    'users': {'list': 'user.list_users', 'view': 'simple'},
    'user_roles': {'list': 'permissions.list_roles', 'view': 'simple'},
    'user_requests': {'list': 'mentor_request.list_request', 'view': 'simple'},
    'token_requests': {'list': 'mentor_request.token_list', 'view': 'simple'},
    'messages': {'list': 'message.list_message', 'view': 'simple'},
    'offers': {'list': 'offers.list_offers', 'view': 'simple', 'parent': 'settings'},
    'audit_log': {'list': 'admin.audit_log', 'view': 'simple', 'parent': 'admin'},
    'activity_log': {'list': 'admin.legacy_activity_log', 'view': 'simple', 'parent': 'admin'},
    'access_log': {'list': 'admin.access_log', 'view': 'simple', 'parent': 'admin'},
    'webhook_log': {'list': 'admin.webhook_log', 'view': 'simple', 'parent': 'admin'},
    'automated_custom_messages': {'list': 'message.custom_messages_list', 'view': 'simple', 'parent': 'settings'},
    'user' : {'list': 'user.list_users', 'view': 'simple'},
    'portfolios': {'list': 'portfolios.list_portfolios','view': 'simple'},
    'operational_entities_l0': {'list': 'entities.list_entities', 'list_arg': ('level', 0), 'view': 'simple'},
    'operational_entities_l1': {'list': 'entities.list_entities', 'list_arg': ('level', 1), 'view': 'simple'},
    'operational_entities_l2': {'list': 'entities.list_entities', 'list_arg': ('level', 2), 'view': 'simple'},
    'operational_entities_l3': {'list': 'entities.list_entities', 'list_arg': ('level', 3), 'view': 'simple'},
    'operational_entities_l4': {'list': 'entities.list_entities', 'list_arg': ('level', 4), 'view': 'simple'},
    'client_groups': {'list': 'entities.list_client_groups', 'view': 'simple'},
    'hierarchy': {'list': 'admin.view_full_hierarchy', 'view': 'simple', 'parent': 'admin'},
    'billing_information': {'list': 'admin.billing', 'view': 'simple', 'parent': 'admin'},
    'add-on_offers': {'list': 'contract.addons_configuration', 'view': 'simple', 'parent': 'settings', 'hash': 'offers'},
    'add-on_bundles': {'list': 'contract.addons_configuration', 'view': 'simple', 'parent': 'settings', 'hash': 'bundles'},
    'add-on_categories': {'list': 'contract.addons_configuration', 'view': 'simple', 'parent': 'settings', 'hash': 'categories'},
    'tasks': {'list': 'task_manager.list_tasks','view': 'simple'},
    'automations': {'list': 'automations.list_automations', 'view': 'simple', 'parent': 'settings'},
}

def get_page_config(page_name):
    return BREADCRUMBS_CONFIG.get(page_name.lower().replace(' ', '_'))


def breadcrumb_link(page_name):
    conf = get_page_config(page_name)
    hash = '#'+conf.get('hash') if conf.get('hash') else ''
    if not conf.get('list_arg'):
        return url_for(conf.get('list'))+hash
    else:
        return url_for(conf.get('list'), **{conf.get('list_arg')[0]: conf.get('list_arg')[1]})+hash


def breadcrumb_object_name(page_name, object):
    conf = get_page_config(page_name)
    if conf.get('view') == 'simple':
        return object.get_display_id()
    return conf.get('name')(object)


def breadcrumb_object_link(page_name, object):
    conf = get_page_config(page_name)
    if conf.get('view') == 'simple':
        return object.get_link()
    return url_for(conf.get('view'), **{conf.get('view_arg')[0]: conf.get('view_arg')[1](object)})

def breadcrumb_parent(page_name):
    return get_page_config(page_name).get('parent')

@app.context_processor
def breadcrumb_link_processor():
    return dict(
        breadcrumb_link=breadcrumb_link,
        breadcrumb_object_link=breadcrumb_object_link,
        breadcrumb_object_name=breadcrumb_object_name,
        breadcrumb_parent=breadcrumb_parent
    )



from shared.services.translation_service import TranslationService, NoTranslate
def text_formatter(text, *args, novar=False, force=False, **kwargs):
    #if not novar:
    #    args = ('<var>'+str(a)+'</var>' for a in args)
    #    for key in kwargs:
    #        kwargs.update({key: '<var>'+str(kwargs[key])+'</var>'})
    text = TranslationService.ftext(text, *args, force=force, user=current_user, **kwargs)
    return markupsafe.Markup(markupsafe.Markup(text).unescape())


def is_safe(variable):
    if isinstance(variable, markupsafe.Markup):
        return True
    return False


@app.context_processor
def format_processor():
    return dict(ftext=text_formatter, is_safe=is_safe)


def get_tags():
    return ClientTagService.get_list(current_user)

@app.context_processor
def tags_processor():
    return dict(get_tags=get_tags, get_device_tags=lambda: DeviceTagService.get_list(current_user))


def get_audit_log_link(obj):
    if not obj:
        return
    object_type = obj.__class__.__name__
    if object_type not in AuditLogService.EXLUDED_TYPES:
        return url_for('admin.audit_log', object_type=object_type, object_id=obj.id)

@app.context_processor
def audit_log_link_processor():
    return dict(get_audit_log_link=get_audit_log_link)


@app.before_request
@db_session
def before_request():
    session_lifetime = get_global_setting('SessionLifetime')
    flask.session.permanent = True
    if session_lifetime >= 10:
        app.permanent_session_lifetime = timedelta(minutes=session_lifetime)
        flask.session.modified = True


def split_camel_case(value):
    # Insert a space before each capital letter, but don't touch the first letter
    return re.sub(r'(?<!^)([A-Z])', r' \1', value)

app.jinja_env.filters['split_camel_case'] = split_camel_case
app.jinja_env.filters['get_shop_name'] = lambda id: ((db.Hub.get(id=id).name if db.Hub.get(id=id) else 'Removed') if id != 'all' else 'All')
app.jinja_env.filters['get_lead_status_name'] = lambda id: LeadStatus.get(id=int(id)).name if id != 'all' else 'All'
app.jinja_env.filters['list2dict'] = lambda l: {k: k for k in l}
app.jinja_env.filters['iconfilter_list'] = lambda l: json.dumps([{"id": k, "text": '<i class="material-symbols-rounded black-text tiny">'+k+'</i>  '+k.replace('_', ' ')} for k in l])
app.jinja_env.filters['answers_value_view'] = lambda answers: [a.get_answer_value(use_names=True) for a in answers] if answers else []
app.jinja_env.filters['answers_value'] = lambda answers: [a.get_answer_value(use_names=False) for a in answers] if answers else []
# Those filters are needed because in the select we cannot have boolean values, instead we have "true" or "false" and not "True" or "False"
app.jinja_env.filters['select_answer_value'] = lambda answers: [
    (str(a) if (a and a not in [True, False]) else str(a).lower()) for a in answers] if answers else []
app.jinja_env.filters['clean_answer_value'] = lambda a: str(a) if (a and a not in [True, False]) else str(a).lower()
app.jinja_env.filters['notranslate'] = lambda a: NoTranslate(a)
def extract_user_agent(user_agent):
    platform, rest = user_agent.split(' ')
    browser, version = rest.split('/')
    return {
        'platform': platform,
        'browser': browser,
        'version': version
    }
app.jinja_env.filters['extract_user_agent'] = extract_user_agent
app.jinja_env.filters['permission_spacer'] = permission_spacer
app.jinja_env.filters['dateformat'] = lambda date: TranslationService.ftext('{day} '+date.strftime("%b")+' {year}', day=date.strftime("%d"), year=date.strftime("%Y"))
app.jinja_env.filters['timetodate'] = datetime.fromtimestamp
app.jinja_env.filters['pretty_json'] = lambda x: json.dumps(x, indent=4, default=json_serializer)

def escape_quote(text):
    quote = "'"
    if quote in text:
        text = ''.join([c if ord(c) != 39 else '\'' for c in text])
    return text
app.jinja_env.filters['escapequote'] = escape_quote


def tagListHelper(tag):
    return '<span class="badge rounded-pill bg-label-secondary '+tag.style+'-badge">'+tag.name+'</span>'
app.jinja_env.filters['tagsList'] = tagListHelper


def tagInput(existing_tags):
    existing_tags = [{'value': tag.name, 'style': tag.style, 'id': tag.id} for tag in existing_tags]
    return json.dumps(existing_tags)
app.jinja_env.filters['tagInput'] = tagInput

def entityChipListHelper(entity):
    return '<div class="chip"><i class="material-symbols-rounded tiny">'+OperationalEntitiesHelper.get_icon(entity.level)+'</i>'+entity.name+'</div>'
app.jinja_env.filters['entityChipList'] = entityChipListHelper


def entity_icon_helper(entity):
    return OperationalEntitiesHelper.get_icon(entity.level)
app.jinja_env.filters['entityIcon'] = entity_icon_helper


def entityIDChipListHelper(entity_id):
    entity = db.OperationalEntity.get(id=entity_id)
    return entityChipListHelper(entity)


app.jinja_env.filters['entityIDChipList'] = entityIDChipListHelper

def entityFromEntityID(entity_id):
    return db.OperationalEntity.get(id=entity_id)
app.jinja_env.filters['entityFromEntityID'] = entityFromEntityID

def dict_mapper(opts):
    objs = opts[0]
    k = opts[1]
    v = opts[2]
    return {getattr(o, k): getattr(o, v) for o in objs}
app.jinja_env.filters['dictMapper'] = dict_mapper

def dict_mapper_key(opts):
    objs = opts[0]
    v = opts[1]
    return {k: o.get(v) for k,o in objs.items()}
app.jinja_env.filters['dictMapperKey'] = dict_mapper_key

def list_mapper(objs):
    return {o: o for o in objs}
app.jinja_env.filters['listMapper'] = list_mapper


def dict_list_mapper(opts):
    objs = opts[0]
    k = opts[1]
    return [getattr(o, k) for o in objs]
app.jinja_env.filters['dictListMapper'] = dict_list_mapper


@pass_context
def dynamic_macro(context, macro_name, *args, **kwargs):
    if '.' in macro_name:
        v = macro_name.split('.')
        return getattr(context[v[0]], v[1])(*args, **kwargs)
    return context.vars[macro_name](*args, **kwargs)


app.jinja_env.filters['macro'] = dynamic_macro

def format_task_text(text, task, color=None, plain_text=False):
    """Replaces placeholders in task name or instructions with links and optionally applies a color class to the links."""
    
    # Function to safely get task attributes
    def safe_get(attribute):
        """Safely retrieves an attribute from the task."""
        if hasattr(task, attribute):
            return getattr(task, attribute, None)
        return None
    
    # Replace {contract} with contract_link
    if '{contract}' in text:
        contract = safe_get('contract')
        if contract:
            if color:
                text = text.replace(
                    '{contract}', 
                    f'<a class="{color}" href="{url_for("contract.view_contract", contract_reference=contract.reference)}">{contract.reference}</a>'
                )
            else:
                text = text.replace(
                    '{contract}', 
                    f'<a href="{url_for("contract.view_contract", contract_reference=contract.reference)}">{contract.reference}</a>'
                )
        else:
            text = text.replace('{contract}', '[Contract Not Available]')
    
    # Replace {client} with client_link
    if '{client}' in text:
        client = safe_get('client')
        if client:
            if color:
                text = text.replace(
                    '{client}', 
                    f'<a class="{color}" href="{url_for("client.view_client", client_id=client.id)}">{client.full_name}</a>'
                )
            else:
                text = text.replace(
                    '{client}', 
                    f'<a href="{url_for("client.view_client", client_id=client.id)}">{client.full_name}</a>'
                )
        else:
            text = text.replace('{client}', '[Client Not Available]')
    
    # Replace {device} with device_link
    if '{device}' in text:
        device = safe_get('device')
        if device:
            if color:
                text = text.replace(
                    '{device}', 
                    f'<a class="{color}" href="{url_for("device.view_device", device_id=device.id)}">{device.get_display_name()}</a>'
                )
            else:
                text = text.replace(
                    '{device}', 
                    f'<a href="{url_for("device.view_device", device_id=device.id)}">{device.get_display_name()}</a>'
                )
        else:
            text = text.replace('{device}', '[Device Not Available]')
    
    # Replace {lead} with lead_link
    if '{lead}' in text:
        lead = safe_get('lead')
        if lead:
            if color:
                text = text.replace(
                    '{lead}', 
                    f'<a class="{color}" href="{url_for("leads.view_lead", lead_id=lead.id)}">{lead.person.full_name}</a>'
                )
            else:
                text = text.replace(
                    '{lead}', 
                    f'<a href="{url_for("leads.view_lead", lead_id=lead.id)}">{lead.person.full_name}</a>'
                )
        else:
            text = text.replace('{lead}', '[Lead Not Available]')
    
    # Handle plain text processing
    if plain_text:
        text = strip_html(text)
        text = text.replace('\n', '<br>')  # convert newlines to <br> tags
        text = strip_markdown(text)  # Remove markdown formatting if needed
    else:
        text = markdown(text)  # Process markdown content
    
    return markupsafe.Markup(markupsafe.Markup(text).unescape())  # Return safe HTML content
app.jinja_env.filters['format_task_text'] = format_task_text

# Function to remove HTML tags and return plain text
def strip_html(text):
    if text:
        return re.sub(r'<.*?>', '', text)  # This regex will remove all HTML tags
    return text

# Register the filter in Flask
app.jinja_env.filters['strip_html'] = strip_html

def strip_markdown(text, full=False):
    # Remove headers (e.g., # Heading)
    text = re.sub(r'^\s{0,3}#{1,6}\s*', '', text, flags=re.MULTILINE)
    # Remove emphasis (**bold**, *italic*, __bold__, _italic_)
    text = re.sub(r'(\*{1,2}|_{1,2})(.*?)\1', r'\2', text)

    # Remove strikethrough (~~text~~)
    text = re.sub(r'~~(.*?)~~', r'\1', text)

    # Remove inline code (`code`)
    text = re.sub(r'`(.+?)`', r'\1', text)

    # Remove links but keep the text [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove images but keep alt text ![alt](url)
    text = re.sub(r'!\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove blockquotes ("> text" → "text")
    text = re.sub(r'^\s*>+\s?', '', text, flags=re.MULTILINE)

    if full:
        # Remove unordered list markers (-, *, +) but preserve text
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)

        # Remove ordered list markers (1., 2., etc.), preserving numbers
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

        # Remove horizontal rules (---, ***, ___)
        text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

        # Remove extra spaces
        text = re.sub(r'\s{2,}', ' ', text).strip()

    return text

app.jinja_env.filters['strip_markdown'] = strip_markdown

# Define the Jinja context function
def task_dropdown():
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return ''

    # Fetch active tasks assigned to the current user
    tasks = TaskService.get_list(
        current_user=current_user,
        assigned_to=current_user,
        hide_historical_tasks=True
    ).order_by(lambda t: t.id)
    now = datetime.now()

    # Prepare the "View All Tasks" link if there are more than 10 tasks
    task_count = tasks.count()
    show_more_link = task_count > 10

    # Render the HTML for the dropdown list
    return render_template("task_mini_menu.html", tasks=tasks[:10], task_count=task_count, show_more_link=show_more_link, now=now)

# Register the custom function in Flask so it can be used globally in Jinja templates
app.jinja_env.globals['task_dropdown'] = task_dropdown

