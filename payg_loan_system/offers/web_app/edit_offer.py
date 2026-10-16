from flask_login import login_required, current_user
from flask import redirect, request, url_for,  flash
from pony.orm import db_session
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from shared.helpers.authorizer import authorizer
import config
from shared.helpers.select2 import render
from stock_management_system.services.product_sub_type_service import ProductSubTypeService

from . import offer_system

from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.offers.models import OfferType


@offer_system.route('/edit/<int:offer_id>', methods=['GET'])
@offer_system.route('<int:offer_id>/edit', methods=['GET'])
@login_required
@authorizer('EditOffers')
@db_session
def edit_offers(offer_id):
    this_offer = ListOfferService.get_from_user_and_id(current_user, offer_id)
    if not this_offer:
        flash('The requested offer does not exist or you do not have the permission to see it. ')
        return redirect(url_for('offers.list_offers'))
    
    VALID_OFFER_TYPES = {k:v for k,v in config.OFFERS_HUMAN_READABLE_TYPES.items() if k}
    device_types = DeviceAPIService.get_device_types_and_type_names(include_data_attributes=True, exclude_time_units=True, include_any=True)

    entities_items = OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True)
    product_sub_types = ProductSubTypeService.get_filtered_objects(current_user, device_type=request.args.get('device_type'))

    select2 = {
        'entities_leads': {
            'items' : entities_items,
            'selected': [(e.id, e.name) for e in this_offer.entities_allowed_for_leads],
            'text': 'name'
        },
        'entities_contracts': {
            'items' : entities_items,
            'selected': [(e.id, e.name) for e in this_offer.entities_allowed_for_contracts],
            'text': 'name'
        },
        'product_sub_types':{
            'items': product_sub_types,
            'selected': this_offer.product_sub_type if this_offer.product_sub_type and this_offer.product_sub_type in product_sub_types else None,
            'text': 'name',
            'force_ajax': True
        }
    }

    entities_allowed_for_contracts = [e.id for e in this_offer.entities_allowed_for_contracts]
    entities_allowed_for_leads = [e.id for e in this_offer.entities_allowed_for_leads]
    return render(
        'edit_offers.html',
        entities_allowed_for_contracts=entities_allowed_for_contracts,
        entities_allowed_for_leads=entities_allowed_for_leads,
        this_offer=this_offer,
        select2=select2,
        device_types=device_types,
        OfferType=OfferType, 
        VALID_OFFER_TYPES=VALID_OFFER_TYPES,
        entities=OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True),
        product_models_data=product_sub_types
    )
