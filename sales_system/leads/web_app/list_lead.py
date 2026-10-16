from payg_loan_system.offers.models import OfferType
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.helpers.select2 import render
from constants import LEADS_VIEWS
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from flask_login import login_required, current_user
from flask import request, render_template, flash, url_for, redirect
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from shared.helpers.pagination import Pagination
from sales_system.leads.models.lead import Lead
from sales_system.leads.services.lead_getter_service import LeadGetterService
from ..services.sort_lead_service import LeadSorter
from . import leads
from shared.services.translation_service import TranslationService
from shared.helpers.form_helpers import dateTimePickerToStandard


DEFAULT_COLUMNS = ('last_contact', 'next_contact', 'requested_offer', 'approved_since', 'promised_pay', 'delivery_date')
COLUMNS = {
    StatusCategory.to_be_convinced: ('requested_offer', 'approved_since', 'promised_pay', 'delivery_date'),
    StatusCategory.awaiting_decision: ('last_contact', 'next_contact', 'approved_since', 'promised_pay', 'delivery_date'),
    StatusCategory.awaiting_payment: ('last_contact', 'next_contact', 'requested_offer', 'delivery_date'),
    StatusCategory.awaiting_delivery: ('last_contact', 'next_contact', 'requested_offer', 'approved_since', 'promised_pay')
}


@leads.route('/', methods=['GET', 'POST'])
@login_required
@authorizer(['ViewCreatedLeads', 'ViewLeads'])
@db_session(retry=2)
def list_lead():

    pagination = Pagination.generate(request, default_sort='first_interaction:desc')
    
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    client_group = ClientGroupGetterService.extract_from_user_and_id(current_user, request.args, "client_group_id", strict=False)
    lead_generator = LeadGeneratorGetterService.extract_from_user_and_id(current_user, request.args, "lead_generator_id", strict=False)
    contract_offer = ListOfferService.extract_from_user_and_id(current_user, request.args, "contract_offer_id", strict=False)
    offer_type = request.args.get('offer_type')
    view = request.args.get('view', 'all')
    
    from_delivery_date_str = request.args.get('from_delivery_date', None)
    from_delivery_date = dateTimePickerToStandard(from_delivery_date_str) if from_delivery_date_str else None
    to_delivery_date_str = request.args.get('to_delivery_date', None)
    to_delivery_date = dateTimePickerToStandard(to_delivery_date_str, '23:59') if to_delivery_date_str else None
    leads = LeadGetterService.get_from_filtered_view(
        current_user.reload(),
        view,
        entity=entity,
        portfolio=portfolio,
        client_group=client_group,
        search=pagination.search,
        generated_by=lead_generator,
        contract_offer=contract_offer,
        offer_type=offer_type,
        from_delivery_date=from_delivery_date,
        to_delivery_date=to_delivery_date
    )
    status_count = get_status_count(leads)

    status_categoty_filter_values = []
    option_classes = {}
    status_category_children = {}
    status_to_category = {}
    status_categories_dict = StatusCategory.to_dict()
    for k, v in status_categories_dict.items():
        status_categoty_filter_values.append((k, TranslationService.ftext(v, user=current_user) + '<var> ('+str(status_count[k])+')</var>'))
        option_classes[k] = 'option-group'
        statuses = list(LeadStatus.select(lambda ls: ls.category == v))
        status_ids = [str(ls.id) for ls in statuses]
        status_categoty_filter_values += [(ls.id, ls.name) for ls in statuses]
        option_classes.update({ls.id: 'child-option no-translate' for ls in statuses})
        status_category_children[k] = status_ids
        status_to_category.update({str(ls.id): k for ls in statuses})

    status_id = request.args.get('status', 'all') or 'all'
    if status_id == 'all':
        selected_status_values = ['all']
    else:
        raw_values = [value for value in status_id.split(',') if value]
        selected_status_values = raw_values
        selected_categories = {value for value in raw_values if value in status_category_children}
        selected_status_ids = {int(value) for value in raw_values if value.isdigit()}

        for category_key in selected_categories:
            selected_status_ids.update(int(status_id) for status_id in status_category_children.get(category_key, []))

        if selected_status_ids:
            statuses = LeadStatusService.get_list(current_user, ids=list(selected_status_ids), strict=True)
            leads = leads.filter(lambda l: l.status in list(statuses))
        elif selected_categories:
            category_values = [status_categories_dict[category_key] for category_key in selected_categories]
            leads = leads.filter(lambda l: l.status.category in category_values)

    if selected_status_values == ['all']:
        columns_to_filter = DEFAULT_COLUMNS
    else:
        first_category_key = next((value for value in selected_status_values if value in status_category_children), None)
        if not first_category_key:
            first_status_value = next((value for value in selected_status_values if value.isdigit() and value in status_to_category), None)
            if first_status_value:
                first_category_key = status_to_category[first_status_value]
        category_value = status_categories_dict.get(first_category_key)
        columns_to_filter = COLUMNS.get(category_value, DEFAULT_COLUMNS)

    pagination.objects = LeadSorter.sort(leads, pagination.sort)
    max_selected_statuses = len(StatusCategory.keys())


    select2 = {
        'portfolios': {
            'items': PortfolioGetterService.get_list(current_user),
            'text': 'name',
            'selected': (portfolio.id, portfolio.name) if portfolio else ()
        },
        'client_groups': {
            'items': ClientGroupGetterService.get_list(current_user),
            'text': 'name',
            'selected': (client_group.id, client_group.name) if client_group else ()
        },
        'lead_generators': {
            'items': LeadGeneratorGetterService.get_list(current_user),
            'text': 'full_name',
            'selected': (lead_generator.id, lead_generator.full_name) if lead_generator else ()
        },

        'contract_offers': {
            'items': ListOfferService.get_list(current_user),
            'text': 'name_and_code',
            'selected': (contract_offer.id, contract_offer.name) if contract_offer else ()
        },

        'offer_types': {
            'items':{t: t for t in OfferType.to_list()},
            'raw_format': True,
        },
    }
    
    return render(
        'list_lead.html',
        select2=select2,
        pagination=pagination,
        selected_status=selected_status_values,
        columns_to_filter=columns_to_filter,
        portfolio=portfolio,
        entity=entity,
        view=view,
        views=LEADS_VIEWS,
        status_categoty_filter_values=status_categoty_filter_values,
        option_classes=option_classes,
        status_category_children=status_category_children,
        status_to_category=status_to_category,
        lead_generator=lead_generator,
        client_group=client_group,
        contract_offer=contract_offer,
        offer_type=offer_type,
        from_delivery_date=from_delivery_date,
        to_delivery_date=to_delivery_date,
        max_selected_statuses=max_selected_statuses
    )



def get_status_count(leads):
    counts = {}
    for k, v in StatusCategory.to_dict().items():
        counts[k] = leads.filter(lambda l: l.status.category == v).count()
    return counts
