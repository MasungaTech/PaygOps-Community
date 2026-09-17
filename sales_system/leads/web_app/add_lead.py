from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_list_service import DeviceListService
from payg_loan_system.offers.models import Offer
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from flask import request
from core_system.client.services.client_getter_service import ClientGetterService, Client
from shared.helpers.select2 import render
from shared.services.settings_service import SettingsService
from . import leads
from flask_login import login_required, current_user
from pony import orm
from shared.helpers.authorizer import authorizer


from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from sales_system.leads.services.lead_status_service import LeadStatusService
from config import REASONS_FOR_NOT_BUYING


@leads.route('/add', methods=['GET'])
@login_required
@authorizer('AddLeads', '.list_lead')
@orm.db_session
def add_lead():

    clients = ClientGetterService.get_list(current_user, for_new_contract=True, extra_permission="AddLeads")

    contract_from_params = request.args.get('contract')
    contract = None
    if contract_from_params:
        contract = ContractGetterService.get_from_user_and_properties(current_user, reference=contract_from_params)
    from_client = clients.filter(lambda c: c.id == request.args.get('from_client')).get() if not contract else contract.client
    
    devices = DeviceListService.get_non_used_devices_for_user_list(current_user)

    client_groups = ClientGroupGetterService.get_list(current_user)

    villages = OperationalEntitiesGetterService.get_list(current_user, level=0, extra_permission='AddLeads').order_by(lambda V: V.name)

    lead_generators = LeadGeneratorGetterService.get_list(current_user).order_by(lambda l: l.person.searchable_name)
    default_offer = Offer.get(code="TDO")
    default_lead_generator = current_user.reload().person.leadGenerator

    select2 = {
        'client': {
            'items': clients,
            'selected': from_client,
            'text': 'full_name_and_custom_id' if SettingsService.get_setting('CustomIdEnabled') else 'full_name_and_id',
            'person_search_field': True,
            'force_ajax': True
        }, 
        'devices': {
            'items': devices,
            'text': 'composed_serial',
            'id': 'composed_serial',
            'force_ajax': True
        },
        'client_groups': {
            'items': client_groups,
            'text': 'name',
        },
        'villages': {
            'items': villages,
            'text': 'name',
        },
        'lead_generators': {
            'items': lead_generators,
            'text': 'full_name_and_id',
            'selected': default_lead_generator,
            'person_search_field': True
        },
        'portfolios': {
            'items': PortfolioGetterService.get_list(current_user),
            'text': 'name'
        }
    }

    # We put that here to skip loading all the rest
    if 'source' in request.args and request.args['source'] in select2:
        return render(None, select2=select2)

    reasons_for_not_buying = dict(sorted(REASONS_FOR_NOT_BUYING.items(),key = lambda kv:(kv[1], kv[0])))
    lead_statuses = LeadStatusService.get_allowed_statuses_for_new_lead(current_user).order_by(lambda s: (s.category, s.order))

    return render(
        'add_lead.html',
        default_lead_generator=default_lead_generator,
        lead_statuses=lead_statuses,
        reasons_for_not_buying=reasons_for_not_buying,
        villages=villages,
        lead_generators=lead_generators,
        can_remove_offer=True,
        select2=select2,
        from_client=from_client,
        client_groups=client_groups,
        contract=contract,
        default_offer=default_offer
    )
