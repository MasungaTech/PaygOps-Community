from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from core_system.client.services.client_getter_service import ClientGetterService
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.helpers.select2 import render
from shared.services.settings_service import SettingsService
from . import leads
from flask_login import login_required, current_user
from flask import render_template
from pony import orm
from shared.helpers.authorizer import authorizer
from payg_loan_system.devices.device_list_service import DeviceListService
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from config import REASONS_FOR_NOT_BUYING


@leads.route('<int:lead_id>/edit/status_form', methods=['GET'])
@login_required
@authorizer('EditLeads', '.list_lead')
@orm.db_session
def edit_lead_status(lead_id):
    this_lead = LeadGetterService.get_from_user_and_id(current_user, lead_id, strict=True, main_resource=True)
    reasons_for_not_buying = dict(sorted(REASONS_FOR_NOT_BUYING.items(),key = lambda kv:(kv[1], kv[0])))
    lead_statuses = LeadStatusChangeService.get_allowed_statuses_from_lead(this_lead, current_user, manual=True).order_by(lambda s: (s.category, s.order))
    return render_template(
        'async_lead_views.html',
        view='status_info',
        Lead=this_lead,
        lead_statuses=lead_statuses,
        reasons_for_not_buying=reasons_for_not_buying
    )


@leads.route('<int:lead_id>/edit/general_info_form', methods=['GET'])
@login_required
@authorizer('EditLeads', '.list_lead')
@orm.db_session
def edit_lead_general_info(lead_id):
    this_lead = LeadGetterService.get_from_user_and_id(current_user, lead_id, strict=True, main_resource=True)

    villages = OperationalEntitiesGetterService.get_list(current_user, level=0, extra_permission='EditLeads').order_by(lambda vi: vi.name)
    
    offers = {o.id: o.name for o in ListOfferService.get_list(
        current_user, in_use_for_new_clients_only=True, current_offer=this_lead.offer
    ).without_distinct().order_by(lambda o: o.name)}
    can_remove_offer = this_lead.awaiting_information or this_lead.to_be_convinced

    clients = ClientGetterService.get_list(current_user, for_new_contract=True)
    from_client = this_lead.person.client

    custom_id_enabled = SettingsService.get_setting('CustomIdEnabled')
    custom_id_required = SettingsService.get_setting('CustomIdMandatory')
    custom_id_text = SettingsService.get_setting('CustomId') or 'Custom ID' + ('*' if custom_id_required else '')
    
    client_groups = ClientGroupGetterService.get_list(current_user)
    lead_in_restricted_status = LeadStatusService.lead_is_in_restricted_status(this_lead)
    restrict_editing = lead_in_restricted_status and not current_user.can_access('EditRestrictedPersonalDetailsLeads', person=this_lead.person)
    select2 = {
        'client': {
            'items': clients,
            'selected': (from_client.id, from_client.full_name_and_custom_id if custom_id_enabled else from_client.full_name_and_id) if from_client else None,
            'text': 'full_name_and_custom_id' if custom_id_enabled else 'full_name_and_id',
            'person_search_field': True
        },
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
        'portfolios': {
            'items': PortfolioGetterService.get_list(current_user),
            'selected': this_lead.portfolio if this_lead.portfolio else None,
            'text': 'name'
        }
    }

    return render('async_lead_views.html',
        view='general_info',
        offers=offers,
        Lead=this_lead,
        Villages=villages,
        can_remove_offer=can_remove_offer,
        select2=select2,
        from_client=from_client,
        client_groups=client_groups,
        custom_id_enabled=custom_id_enabled,
        custom_id_required=custom_id_required,
        custom_id_text=custom_id_text,
        restrict_editing=restrict_editing
    )


@leads.route('<int:lead_id>/edit/entry_info_form', methods=['GET'])
@login_required
@authorizer('EditLeads', '.list_lead')
@orm.db_session
def edit_lead_entry_info(lead_id):
    this_lead = LeadGetterService.get_from_user_and_id(current_user, lead_id, strict=True, main_resource=True)
    lead_generators = LeadGeneratorGetterService.get_list(current_user).order_by(lambda l: l.person.searchable_name)
    
    select2 = {
        'lead_generators': {
            'items': lead_generators,
            'text': 'full_name_and_id',
            'person_search_field': True,
            'selected': (this_lead.generator.id, this_lead.generator.full_name_and_id)
        }
    }

    return render('async_lead_views.html',
                    view='entry_info',
                    select2=select2,
                    Lead=this_lead,
                    lead_generators=lead_generators)


@leads.route('<int:lead_id>/edit/offer_form', methods=['GET'])
@login_required
@authorizer('EditLeads', '.list_lead')
@orm.db_session
def edit_offer(lead_id):
    this_lead = LeadGetterService.get_from_user_and_id(current_user, lead_id, strict=True, main_resource=True)
    return render('async_lead_views.html',
                    select2={},
                    view='offer_form',
                    Lead=this_lead)


@leads.route('<int:lead_id>/edit/device_form', methods=['GET'])
@login_required
@authorizer('EditLeads', '.list_lead')
@orm.db_session
def edit_device(lead_id):
    this_lead = LeadGetterService.get_from_user_and_id(current_user, lead_id, strict=True, main_resource=True)

    devices = DeviceListService.get_non_used_devices_for_user_list(current_user, offer=this_lead.offer)
    select2 = {
        'devices': {
            'items': devices,
            'text': 'composed_serial',
            'id': 'composed_serial',
            'force_ajax': True
        }
    }

    return render(
        'async_lead_views.html',
        view='device_form',
        select2=select2,
        Lead=this_lead
    )