import json
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.client.models import Client
from payg_loan_system.offers.models import Offer, OfferType
from flask_login import login_required, current_user
from flask import render_template, request
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from payg_loan_system.offers.services.list_offer_service import ListOfferService, OfferSorter
from shared.helpers.pagination import Pagination
from . import offer_system


@offer_system.route('/select2_list', methods=['GET', 'POST'])
@login_required
@authorizer('ViewOffers')
@db_session
def list_offers_select2():
    entity_id = None
    from_client_id = request.args.get('for_lead_from_client_id')
    if from_client_id:
        client = Client.get(id=from_client_id)
        entity_id = client.person.village.id if client else None
    from_lead_id = request.args.get('for_lead_entity_id')
    entity_id = from_lead_id if from_lead_id else None
    for_lead_entity = OperationalEntitiesGetterService.get_from_user_and_id(current_user, entity_id, strict=False)
    offers = ListOfferService.get_list(
        current_user=current_user,
        active_filter='active',
        search=request.args.get('term', ''),
        for_lead_entity=for_lead_entity
    ).order_by(Offer.id)

    results = {
        'results': [
            {
                'id': item.id,
                'text': item.name,
                'data': {
                    'linked-to-product': item.linked_to_product
                }
            } for item in offers]
    }
    return json.dumps(results)


@offer_system.route('/', methods=['GET', 'POST'])
@login_required
@authorizer('ViewOffers')
@db_session
def list_offers():
    if request.method == 'POST':
        search = request.form.get('search', '')
        active_filter = request.form.get('active_filter', 'default')
        otype = request.form.get('type', '')
    else:
        search = request.args.get('search', '')
        active_filter = request.args.get('active_filter', 'default')
        otype = request.args.get('type', '')

    offers = ListOfferService.get_list(
        current_user=current_user, active_filter=active_filter, search=search, otype=otype
    ).order_by(Offer.id)

    pagination = Pagination.generate(request, default_sort='id:desc')
    pagination.objects = OfferSorter.sort(offers, pagination.sort)

    return render_template('list_offers.html',
                           pagination=pagination,
                           search=search,
                           active_filter=active_filter,
                           otype=otype,
                           types={t: t for t in OfferType.to_list()})
