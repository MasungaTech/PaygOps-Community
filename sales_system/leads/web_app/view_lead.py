import json
from payg_loan_system.contracts.services.addon_category_service import AddonCategoryService
from payg_loan_system.contracts.services.addon_bundle_list_service import AddonBundleListService
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_list_service import DeviceListService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.helpers.select2 import render
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.contracts.models.addons_model import AddOnLoanExtensionMode, AddOnOffer, AddOnOfferVersion, AddOnType
from payg_loan_system.offers.models import OfferType
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from shared.logger.loggers import Error
from survey_system.services.form_getter_service import FormVersionGetterService
from survey_system.services.survey_answer_getter_service import SurveyAnswerGetterService
from . import leads
from flask_login import login_required, current_user
from flask import flash, redirect, url_for, request, render_template
from core_system.client.services.client_getter_service import ClientGetterService
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from pony import orm
from shared.helpers.authorizer import authorizer
from shared.services.settings_service import SettingsService

from sales_system.leads.services.lead_getter_service import LeadGetterService
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from core_system.person.services.form_visibility_rule_getter import FormVisibilityRuleGetterService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService


def check_availability(*args, **karwgs):
    try:
        AddonService.check_addon_offer_available(*args, **karwgs)
    except Error:
        return False
    return True


def preprocess_lead(lead_id):
    this_lead = LeadGetterService.get_from_user_and_id(current_user, lead_id)
    if not this_lead:
        return
    if not 'source' in request.args:
        # We do that to make sure  in case of survey update that the Lead is indeed updated and update old Leads
        this_lead = LeadStatusChangeService.update(this_lead) or this_lead # Should not be needed anymore
    

def process_lead(lead_id):
    this_lead = LeadGetterService.get_from_user_and_id(current_user, lead_id)
    if not this_lead:
        flash('Lead does not exist or you do not have the permission to see it. ')
        return redirect(url_for('leads.list_lead'))

    if 'source' in request.args and request.args['source'] == 'client':
        clients = ClientGetterService.get_list(current_user, for_new_contract=True)
        from_client = this_lead.person.client
        custom_id_enabled = SettingsService.get_setting('CustomIdEnabled')
        select2 = {
            'client': {
                'items': clients,
                'selected': (from_client.id, from_client.full_name_and_custom_id if custom_id_enabled else from_client.full_name_and_id) if from_client else None,
                'text': 'full_name_and_custom_id' if custom_id_enabled else 'full_name_and_id',
                'person_search_field': True
            }
        }
        return render('view_lead.html', select2=select2)
    
    if 'source' in request.args and request.args['source'] == 'devices':
        devices = DeviceListService.get_non_used_devices_for_user_list(current_user, this_lead.offer)
        d = this_lead.allocated_device
        select2 = {
            'devices': {
                'items': devices,
                'selected': (d.composed_serial, d.composed_serial) if d else None,
                'text': 'composed_serial',
                'id': 'composed_serial'
            }
        }
        return render('view_lead.html', select2=select2)

    if 'source' in request.args and request.args['source'] in ['client_groups', 'villages', 'lead_generators']:
        client_groups = ClientGroupGetterService.get_list(current_user)
        villages = OperationalEntitiesGetterService.get_list(current_user, level=0, extra_permission='EditLeads').order_by(lambda vi: vi.name)
        lead_generators = LeadGeneratorGetterService.get_list(current_user).order_by(lambda l: l.person.searchable_name)
        select2 = {
            'client_groups': {
            'items': client_groups,
            'selected': (this_lead.person.client_group.id, this_lead.person.client_group.name) if this_lead.person.client_group else (),
            'text': 'name'
            },
            'villages': {
                'items': villages,
                'selected': (this_lead.person.village.id, this_lead.person.village.name),
                'text': 'name'
            },
            'lead_generators': {
                'items': lead_generators,
                'text': 'full_name_and_id',
                'person_search_field': True,
                'selected': this_lead.generator
            }
        }
        return render(None, select2=select2)

    offers = AddonOfferGetterService.get_list(current_user, for_lead=this_lead).order_by(AddOnOffer.code)

    bundles = AddonBundleListService.get_list(current_user, for_offer=this_lead.offer, for_entity_lead=this_lead.person.village)
    category = AddonCategoryService.extract_from_user_and_id(current_user, request.args, 'category')
    if category:
        offers = offers.filter(lambda o: o in category.covered_offers)
        bundles = bundles.filter(lambda o: o in category.covered_bundles)
    bundles_available = bundles.exists()
    
    offer_version = AddOnOfferVersion.get(id=request.args.get('add_on_offer', -1))
    devices = DeviceListService.get_non_used_devices_for_user_list(current_user, add_on_offer=offer_version.offer if offer_version else None)
    portfolios = PortfolioGetterService.get_filtered_objects(current_user=current_user)
    select2 = {
        'offer_id_selector': {
            'items': offers,
            'id': 'version_for_sales_id',
            'text': 'name_and_version_for_sales'
        },
        'bundle_id_selector': {
            'items': bundles,
            'text': 'name'
        },
        'add_on_devices': {
            'items': devices,
            'text': 'composed_serial',
            'force_ajax': True,
            'id': 'composed_serial'
        },
        'portfolios': {
            'items': portfolios,
            'selected': this_lead.portfolio,
            'text': 'name'
        }
    }
    if 'source' in request.args and request.args['source'] in ['offer_id_selector', 'bundle_id_selector']:
        return render(None, select2=select2)

    leads_answered_surveys = FormVisibilityRuleGetterService.get_answers_for_lead(this_lead)
    leads_not_answered_surveys = FormVisibilityRuleGetterService.get_not_answered_surveys(lead=this_lead)
    required_forms = FormVisibilityRuleGetterService.get_forms(lead=this_lead, required=True)

    offers_data_select = {}
    offers_data_full = {}
    # We only need to load that date if we show the addon editor
    # It's quite a lot of data so better not to do it when not needed
    if this_lead.can_edit_offer:
        offers_data_full = AddonOfferGetterService.formatted_addon_offer_list(offers)
        # We do this to ensure we have the data for the current addons even if they're not available for sales anymore
        for addon in this_lead.addons:
            if addon.offer_version not in offers:
                offers_data_full.update(AddonOfferGetterService.formatted_addon_offer_list([addon.offer_version.offer], raw=addon.offer_version))
        offers_data_select = {o.version_for_sales.id: o.name_and_version_for_sales for o in offers}

    approve_statuses = LeadStatus.select(lambda s: s.category in StatusCategory.awaiting_payment)

    discarded_statuses = LeadStatus.select(lambda s: s.category in [StatusCategory.discarded, StatusCategory.inactive])
    offers_data = {o.id: o.name for o in ListOfferService.get_list(
        current_user, in_use_for_new_clients_only=True, current_offer=this_lead.offer, for_lead_entity=this_lead.person.village
    ).without_distinct().order_by(lambda o: o.name)}

    categories_available = AddonCategoryService.get_list(current_user).exists()
    can_remove_offer = this_lead.awaiting_information or this_lead.to_be_convinced
    user_has_permission_to_erase_phones = current_user.reload().can_access('DeletePhoneNumbers', entity=this_lead.person.village) and this_lead.offer_editing_locked
    lead_in_restricted_status = LeadStatusService.lead_is_in_restricted_status(this_lead)
    restrict_editing = lead_in_restricted_status and not current_user.can_access('EditRestrictedPersonalDetailsLeads', person=this_lead.person)
    formattedCustomButtons = []
    settings = SettingsService.get_setting('customButtonConfiguration')
    if settings:
        for button in settings:
            if button.get('TargetPage') == 'lead' and button.get('TargetUrl'):
                button['TargetUrl'] = button['TargetUrl'].format(
                    lead_id=this_lead.id,
                    lead_name=this_lead.full_name,
                    custom_id=this_lead.person.custom_id or '',
                    lead_phone_number=this_lead.person.contactPhone.number if this_lead.person.contactPhone else '',
                    user_id=current_user.id,
                    user_name=current_user.full_name,
                )
                formattedCustomButtons.append(button)
    return render(
        'view_lead.html',
        Lead=this_lead,
        person=this_lead.person,
        LeadsSurveys=leads_answered_surveys,
        extra_surveys=leads_not_answered_surveys,
        required_forms=required_forms,
        user_has_permission_to_erase_phones=user_has_permission_to_erase_phones,
        addon_offers=offers_data_select,
        loan_modes={c: AddOnLoanExtensionMode.to_human(c) for c in AddOnLoanExtensionMode.to_list()},
        offers_data=json.dumps(offers_data_full),
        AddOnType=AddOnType,
        AddOnLoanExtensionMode=AddOnLoanExtensionMode,
        OfferType=OfferType,
        ReconciledPaymentType=ReconciledPaymentType,
        approve_statuses=approve_statuses,
        discarded_statuses=discarded_statuses,
        offers=offers_data,
        can_remove_offer=can_remove_offer,
        personIDForSurvey=this_lead.id,
        personType='lead',
        bundles_available=bundles_available,
        categories_available=categories_available,
        formattedCustomButtons=formattedCustomButtons,
        select2=select2,
        check_availability=check_availability,
        restrict_editing=restrict_editing
    )

@leads.route('/<int:lead_id>', methods=['GET'])
@login_required
@authorizer(['ViewLeads', 'ViewCreatedLeads'], '.list_lead')
@orm.db_session(retry=1)
def view_lead(lead_id):
    with orm.db_session:
        preprocess_lead(lead_id)
    with orm.db_session():
        return process_lead(lead_id)
