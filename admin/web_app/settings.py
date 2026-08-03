import json
from shared.services.email_sender import EmailSender
from shared.services.web_menu_service import WebMenuService
from stock_management_system.services.product_sub_type_service import ProductSubTypeService
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.model.device import Device
from payg_loan_system.offers.models import OfferType
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.logger.loggers import Error
from flask_login import login_required, current_user
from flask import request, render_template, jsonify, redirect, url_for, abort
from pony.orm import db_session, select
import config
if config.ENABLE_ENTERPRISE_FEATURES:
    from app_builder_system.user_journey_editor.services.user_journey_service import UserJourneyService

from worker_app.tasks.reconcile_orphaned_payments import reconcile_orphaned_payments
from shared.services.translation_service import TranslationService
from payg_loan_system.offers.models import Offer, OfferType
from core_system.person.models.form_visibility import FormVisibilityRule
from survey_system.models.forms import Form
from munch import Munch

from shared.helpers.authorizer import authorizer
from shared.helpers.form_helpers import dateTimePickerToStandard
from shared.helpers.select2 import render
from shared.services.settings_service import SettingsService
from shared.helpers.locale_helper import get_all_available_currencies_from_json

from data_system.services.custom_dashboard_service import CustomDashboardService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from payg_loan_system.devices.services.offline_token_config_service import OfflineTokenConfigService
from shared.services.celery_queue_service import CeleryQueueService
from sales_system.lead_generator.services.lead_generator_type_service import LeadGeneratorTypeService
import config
from . import administration


@administration.route('/settings', methods=["GET", "POST"])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def settings_menu():
    return render_template('settings/settings_menu.html')


@administration.route('/configuration/general', methods=["GET"])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def settings_editor_get():
    currencies = get_all_available_currencies_from_json()
    custom_dashboard_names = CustomDashboardService.get_custom_dashboards_list()

    AvailableDeviceTypeList = DeviceAPIService.get_device_types_and_type_names()
    AvailableDeviceTypeList.update({'DISABLED': 'Disabled'})
    device_api_settings = SettingsService.get_setting('AllDeviceAPIS')
    device_types = []
    for device_type in device_api_settings.keys():
        if device_api_settings[device_type].get('offline_mode') == 'ENABLED':
            device_types.append({
                'name': device_type,
                'full_name': device_api_settings[device_type].get('device_api_full_name'),
                'offline_token_config': OfflineTokenConfigService.get_config_for_device_type(device_type)
            })

    menu = WebMenuService.get_menu(current_user)
    menus = {}
    for m,d in menu.items():
        if menu.get(m, {}).get('children', None):
            menus[m] = d['label']
    if config.ENABLE_ENTERPRISE_FEATURES:
        user_journeys = list(UserJourneyService.get_list(current_user))
    else:
        user_journeys = []
    user_journeys_dict_list = [u.to_dict() 
                               | {"current_version": u.get_current_version().id if u.get_current_version() else None} \
                               | {"steps": u.get_steps_for_current_version() if u.get_steps_for_current_version() else []} \
                               for u in user_journeys]
    custom_buttom_types = {
                            'user_journey': 'User Journey', 
                            'custom_dashboard': 'Custom Dashboard'
                           }
    
    return render_template(
        'settings/settings_editor_general.html',
        AvailableDeviceTypeList=AvailableDeviceTypeList,
        device_types=device_types,
        custom_dashboard_names=custom_dashboard_names,
        currencies=currencies,
        menus=menus,
        user_journeys=user_journeys,
        user_journeys_dict_list=user_journeys_dict_list,
        custom_buttom_types=custom_buttom_types,
        WEB_MENU_INFO_UNFILTERED=WebMenuService.get_menu(current_user, filtered=False)
    )


@administration.route('/configuration/general/offline_token_config/<name>', methods=["POST"])
@login_required
@authorizer('CustomizePlatformAdmin')
@db_session
def platform_customization_offline_token(name):
    try:
        data = request.json
        OfflineTokenConfigService.edit_device_type_token_config(data.get('offline_token_config'), name)
    except Error as error:
        return {"error_message": str(error)}, 400
    return json.dumps({'success': True}), 200


@administration.route('/configuration/sales', methods=["GET"])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def settings_editor_sales_get():
    lead_statuses_obj = {}
    new_lead_statuses = LeadStatusService.get_allowed_statuses_for_new_lead()
    for lead_status in new_lead_statuses:
        lead_statuses_obj[lead_status.id] = lead_status.name
    lead_statuses = {}
    for cat in StatusCategory.to_list():
        lead_statuses[cat] = LeadStatus.select(lambda s: s.category == cat).order_by(LeadStatus.order)
    lead_statuses_inc_new = {'New Lead': [Munch({'id': '1001', 'name': 'New Lead', 'color': 'main', 'category': 'new'})]}
    lead_statuses_inc_new.update(lead_statuses)
    # For the restricted status selector
    status_categoty_filter_values = []
    option_classes = {}
    for k, v in StatusCategory.to_dict().items():
        status_categoty_filter_values.append((k, TranslationService.ftext(v, user=current_user)))
        option_classes[k] = 'option-group disabled'
        statuses = LeadStatus.select(lambda ls: ls.category == v).order_by(LeadStatus.order)
        status_categoty_filter_values += [(ls.id, ls.name) for ls in statuses]
        option_classes.update({ls.id: 'child-option no-translate' for ls in statuses})

    lg_types = LeadGeneratorTypeService.get_list(current_user, exclude_default=True).order_by(lambda lgt: lgt.name)
    return render_template(
        'settings/settings_editor_sales.html',
        get_statuses_for_category=LeadStatusChangeService.get_allowed_statuses_from_category,
        cat_codes=StatusCategory.to_inv_dict(),
        last_id=select(max(s.id) for s in LeadStatus).first(),
        lead_statuses=lead_statuses,
        lead_statuses_inc_new=lead_statuses_inc_new,
        lead_statuses_obj=lead_statuses_obj,
        status_categoty_filter_values=status_categoty_filter_values,
        option_classes=option_classes,
        lg_types=lg_types,
    )

@administration.route('/configuration/sales/lead_statuses', methods=["POST"])
@login_required
@authorizer('CustomizePlatformAdmin')
@db_session
def settings_editor_sales_lead_statuses():
    try:
        LeadStatusService.edit_statuses(request.json)
    except Error as error:
        return {"error_message": str(error)}, 400
    return json.dumps({'success': True}), 200


@administration.route('/configuration/payments', methods=["GET"])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def settings_editor_payments_get():
    matching_parameters = {k:v.format(custom_id_name=SettingsService.get_setting('CustomId') or 'Custom ID') for k,v in config.AVAILABLE_MATCHING_PARAMETERS.items()}
    return render_template('settings/settings_editor_payments.html', matching_parameters=matching_parameters)


@administration.route('/configuration/personal', methods=["GET"])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def settings_editor_personal_get():
    # For the personal info
    reasons_for_not_buying = dict(sorted(config.REASONS_FOR_NOT_BUYING.items(),key = lambda kv:(kv[1], kv[0])))
    lead_statuses = LeadStatusService.get_allowed_statuses_for_new_lead()
    # For the forms
    available_forms = Form.select(lambda sw: sw.for_clients or sw.for_leads)
    rules = FormVisibilityRule.select().order_by(lambda p: p.order)
    available_forms_data = {form.id: {'name': form.name, 'icon': form.icon, 'scopes': form.allowed_scopes_human()} for form in available_forms}
    forms_select = {form.id: form.name for form in available_forms.order_by(lambda f: f.name)}
    offer_types = {t:t for t in OfferType.to_list()}
    offer_types.update({'specific': 'Specific Offers'})
    available_offers=Offer.select()
    select2 = {
        'offers': {
            'items': available_offers,
            'text': 'name'
        },
    }
    return render('settings/settings_editor_personal.html',
                           select2=select2,
                           reasons_for_not_buying=reasons_for_not_buying,
                           lead_statuses=lead_statuses,
                           forms_select=forms_select,
                           available_forms=available_forms_data,
                           rules=rules,
                           offer_types=offer_types)


@administration.route('/configuration/advanced', methods=["GET"])
@login_required
@authorizer('SuperAdmin')
@db_session
def settings_editor_get_advanced():
    reconcile_orphaned_payment_is_running = CeleryQueueService.is_task_running(reconcile_orphaned_payments.name)
    available_offer_types = DeviceAPIService.get_available_offer_types_per_device_type()
    used_apis = list(select(d.type for d in Device if d.type != 'NPG'))
    return render_template(
        'settings/settings_editor_advanced.html',
        AvailableOfferTypeList = available_offer_types,
        reconcile_orphaned_payment_is_running=reconcile_orphaned_payment_is_running,
        used_apis=used_apis
    )


@administration.route('/configuration/advanced/reconcile', methods=["POST"])
@login_required
@authorizer('SuperAdmin')
@db_session
def auto_reconcile_payments():
    from payg_loan_system.payments.services.orphaned_payment_service import OrphanedPaymentService
    data = request.json
    from_date = dateTimePickerToStandard(data.get('from_date'))
    to_date = dateTimePickerToStandard(data.get('to_date'))
    exclude_reverted = not data.get('not_exclude_reverted', False)
    orphaned_payments = OrphanedPaymentService.get_orphaned_payments(from_date, to_date, exclude_reverted=exclude_reverted)
    count = orphaned_payments.count()
    # Task with delay
    CeleryQueueService.execute_task(reconcile_orphaned_payments, data.get('from_date'), data.get('to_date'), exclude_reverted)
    return jsonify({'count': count})

@administration.route('/configuration/clients', methods=['GET'])
@login_required
@db_session
@authorizer('CustomizePlatformAdmin')
def settings_editor_clients():
    return render_template('settings/settings_editor_clients.html')

@administration.route('/configuration/inventory', methods=["GET","POST"])
@login_required
@authorizer('ConfigureProductAdmin')
@db_session
def settings_editor_inventory_get():

    product_sub_types = ProductSubTypeService.get_filtered_objects(current_user).order_by(lambda pst: pst.id)
    product_types = DeviceAPIService.get_device_types_and_type_names()
    
    return render_template(
        'settings/settings_editor_inventory.html', 
        product_sub_types=product_sub_types,
        product_types=product_types
    )


@administration.route('/mobile_app_customization_card', methods=['GET', 'POST'])
@login_required
@authorizer('ViewSettingsInterfaceAdmin')
@db_session
def mobile_app_customization_card():
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return abort(404)

    journeys = []
    new_journeys = []
    selected_ids = []
    mobile_app_customization_settings = SettingsService.get_setting("mobileAppCustomizationCardSetting")
    custom_app_menus = SettingsService.get_setting('app_menu') 
    if config.ENABLE_ENTERPRISE_FEATURES:
        journeys = UserJourneyService.get_list(current_user=current_user).order_by(lambda o: o.id)
        new_journeys = journeys.filter(lambda o: o.id not in selected_ids).order_by(lambda o: o.id)
        selected_ids = [int(menu.get('user_journey')) for menu in custom_app_menus if menu.get('user_journey')]
    

    mobile_app_customization_settings = { 
        'enabled': mobile_app_customization_settings.get('enabled', False), 
        'mobile_app_name': mobile_app_customization_settings.get('mobile_app_name'), 
        'app_store_description': mobile_app_customization_settings.get('app_store_description'), 
        'primary_corporate_colour': mobile_app_customization_settings.get('primary_corporate_colour'), 
        'picture_id': mobile_app_customization_settings.get('picture_id'), 
        'available_in_google_play_store': mobile_app_customization_settings.get('available_in_google_play_store', False), 
        'available_in_apple_app_store': mobile_app_customization_settings.get('available_in_apple_app_store', False), 
    }
    return render_template(
        'settings/mobile_app_customization_card.html', 
        mobile_app_customization_settings=mobile_app_customization_settings,
        custom_app_menus=custom_app_menus,
        journeys=journeys,
        new_journeys=new_journeys
    )

def send_mobile_customization_email_notification(app_menu_settings):
    EMAIL_TEMPLATE = f"""Hello! 
                        <br> 
                        <br> 
                        There is a new change in mobile app customization from <b>{current_user.organization}</b> : {current_user.username}. 
                        <br> 
                        <br> 

                        <table>
                            <thead>
                                <tr>
                                    <th>Attribute</th>
                                    <th>Data</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>enabled</td>
                                    <td>{app_menu_settings.get('enabled')}</td>
                                </tr>
                                <tr>
                                    <td>mobile_app_name</td>
                                    <td>{app_menu_settings.get('mobile_app_name')}</td>
                                </tr>
                                <tr>
                                    <td>app_store_description</td>
                                    <td>{app_menu_settings.get('app_store_description')}</td>
                                </tr>
                                <tr>
                                    <td>primary_corporate_colour</td>
                                    <td>{app_menu_settings.get('primary_corporate_colour')}</td>
                                </tr>
                                <tr>
                                    <td>picture_id</td>
                                    <td>
                                        <a href='/{app_menu_settings.get('picture_id')}'>{app_menu_settings.get('picture_id')}</a>
                                    </td>
                                </tr>
                               <tr>
                                    <td>available_in_google_play_store</td>
                                    <td>{'YES' if app_menu_settings.get('available_in_google_play_store') else 'NO'}</td>
                                </tr>
                                <tr>
                                    <td>available_in_apple_app_store</td>
                                    <td>{'YES' if app_menu_settings.get('available_in_apple_app_store') else 'NO'}</td>
                                </tr>
                            </tbody>
                        </table>


                        <br> 
                        <br> 
                        <br> 
                        Kind regards, 
                        <br> 
                        The Paygops Support Team"""
    EmailSender(
                    recipient_name='PaygOps team',
                    recipient='customersuccess@solarisoffgrid.com',
                    subject='Mobile App Customization Update',
                    body=EMAIL_TEMPLATE,
                    html=True
                ).send()
