from datetime import timedelta
from constants import CLIENT_VIEWS
from core_system.client.services.client_tag_getter import ClientTagService
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from payg_loan_system.contracts.services.contract_list_service import ContractListService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from shared.helpers.clock import Clock
from shared.helpers.form_helpers import dateTimePickerToStandard
from shared.helpers.select2 import render
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
import re
from flask_login import login_required, current_user
from flask import request, flash
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from shared.helpers.pagination import Pagination
from payg_loan_system.contracts.services.contract_sorter_service import ContractSorter
from payg_loan_system.offers.models import OfferType
from . import contract
import json
import config

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.interaction_system.web_app.add_interaction_report import getInteractionMethods
    from after_sales_system.interaction_system.model.interaction_report_model import InteractionTopic
else:
    def getInteractionMethods(*_, **__):
        return []

    class _InteractionTopicStub:
        @staticmethod
        def get_ordered_dict():
            return {}

    InteractionTopic = _InteractionTopicStub


def extract_integer(key, name):
    number = request.args.get(key, '')
    if number and not re.fullmatch('-?[0-9]*', number):
        flash(f'{name} has to be an integer number')
        return ''
    return number


@contract.route('/', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@db_session
def list_contracts(task_mode=False):

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    client_group = ClientGroupGetterService.extract_from_user_and_id(current_user, request.args, "client_group_id", strict=False)
    addon_offer = AddonOfferGetterService.extract_from_user_and_id(current_user, request.args, "addon_offer_id", strict=False)
    offer_type = request.args.get('offer_type')
    contract_offer = ListOfferService.extract_from_user_and_id(current_user, request.args, "contract_offer_id", strict=False)
    status = request.args.get('status', 'all')
    delivery_status = request.args.get('delivery_status', 'all')
    with_issues = request.args.get('with_issues', None)
    search = request.args.get('search')
    view = request.args.get('view', 'all')
    min_payment_due = extract_integer('min-payment-due', 'Minimum days before next payment')
    max_payment_due = extract_integer('max-payment-due', 'Maximum days before next payment')
    min_cumulative_days = extract_integer('min-cumulative-days', 'Minimum cumulative days late')
    max_cumulative_days = extract_integer('max-cumulative-days', 'Maximum cumulative days late')
    loan_progress_min = extract_integer('loan_progress_min', 'Loan progress')
    loan_progress_max = extract_integer('loan_progress_max', 'Loan progress')
    from_date_str = request.args.get('from_date', None)
    to_date_str = request.args.get('to_date', None)
    from_date = dateTimePickerToStandard(from_date_str) if from_date_str else None
    to_date = dateTimePickerToStandard(to_date_str, '23:59') if to_date_str else None
    from_delivery_date_str = request.args.get('from_delivery_date', None)
    from_delivery_date = dateTimePickerToStandard(from_delivery_date_str) if from_delivery_date_str else None
    to_delivery_date_str = request.args.get('to_delivery_date', None)
    to_delivery_date = dateTimePickerToStandard(to_delivery_date_str, '23:59') if to_delivery_date_str else None
    tags = request.args.get('tags', '')
    tags = ClientTagService.extract_tags(tags, current_user)
    contracts = ContractGetterService.get_from_filtered_view(
        current_user.reload(),
        view=view,
        entity=entity,
        portfolio=portfolio,
        status=status,
        search=search,
        client_group=client_group,
        min_payment_due=min_payment_due,
        max_payment_due=max_payment_due,
        min_cumulative_days=min_cumulative_days,
        max_cumulative_days=max_cumulative_days,
        addon_offer=addon_offer,
        contract_offer=contract_offer,
        offer_type=offer_type,
        from_date=Clock.localize_to_utc(from_date) if from_date else None,
        to_date=Clock.localize_to_utc(to_date) if to_date else None,
        loan_progress_min=loan_progress_min,
        loan_progress_max=loan_progress_max,
        with_issues=with_issues,
        tags=tags,
        delivery_status=delivery_status,
        from_delivery_date=from_delivery_date,
        to_delivery_date=to_delivery_date
    )

    pagination = Pagination.generate(request)
    pagination.sort = request.args.get('sort', 'id:asc')
    pagination.objects = ContractSorter.sort(contracts, pagination.sort)

    valid_statuses = {
        'all': 'All Contracts',
        'active': 'Active Contracts',
        'defaulted': 'Defaulted Contracts',
        'completed': 'Completed Contracts',
        'cancelled': 'Cancelled Contracts',
        'paused': 'Paused Contracts',
        'late': 'Late Contracts',
        'overpaid': 'Overpaid Contracts',
    }

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
        'addon_offers': {
            'items': AddonOfferGetterService.get_list(current_user),
            'text': 'name',
            'selected': (addon_offer.id, addon_offer.name) if addon_offer else ()
        },
        'contract_offers': {
            'items': ListOfferService.get_list(current_user),
            'text': 'name_and_code',
            'selected': (contract_offer.id, contract_offer.name) if contract_offer else ()
        }
    }

    methods=None
    topics=None
    if task_mode:
        methods=getInteractionMethods()
        topics=InteractionTopic.get_ordered_dict()

    return render(
        'list_contracts.html',
        select2=select2,
        offer_types={t: t for t in OfferType.to_list()},
        pagination=pagination,
        status=status,
        entity=entity,
        portfolio=portfolio,
        client_group=client_group,
        addon_offer=addon_offer,
        min_payment_due=min_payment_due,
        max_payment_due=max_payment_due,
        min_cumulative_days=min_cumulative_days,
        max_cumulative_days=max_cumulative_days,
        contract_offer=contract_offer,
        OfferType=OfferType,
        valid_statuses=valid_statuses,
        view=view,
        views=CLIENT_VIEWS,
        tags=tags,
        offer_type=offer_type,
        from_date=from_date,
        to_date=to_date,
        loan_progress_min=loan_progress_min,
        loan_progress_max=loan_progress_max, 
        with_issues=with_issues,
        task_mode=task_mode,
        methods=methods,
        topics=topics,
        delivery_status=delivery_status,
        from_delivery_date=from_delivery_date,
        to_delivery_date=to_delivery_date
    )
