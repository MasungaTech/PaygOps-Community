from stock_management_system.services.product_sub_type_service import ProductSubTypeService
from flask_login import login_required, current_user
from flask import request
from pony.orm import db_session
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from shared.helpers.authorizer import authorizer
from shared.services.settings_service import SettingsService

from . import offer_system

from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.offers.models import OfferType
import config
from shared.helpers.select2 import render

@offer_system.route('/add', methods=['GET', 'POST'])
@login_required
@authorizer('AddOffers')
@db_session
def add_offers():
    device_types = DeviceAPIService.get_device_types_and_type_names(
        include_data_attributes=True,
        exclude_time_units=True,
        include_any=True
    )
    
    product_sub_types = ProductSubTypeService.get_filtered_objects(current_user, device_type=request.args.get('device_type'))
    
    VALID_OFFER_TYPES = {k: v for k, v in config.OFFERS_HUMAN_READABLE_TYPES.items() if k}

    feature_toggles = SettingsService.get_setting('FeatureToggles')
    if not feature_toggles['LumpSumContracts']:
        VALID_OFFER_TYPES.pop('Lump Sum')
    if not feature_toggles['LoanAndSubscriptionContracts']:
        VALID_OFFER_TYPES.pop('Loan')
        VALID_OFFER_TYPES.pop('Time Based')
        VALID_OFFER_TYPES.pop('Usage Based')
    days_of_month = list(range(1, 32))

    entities_items = OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True)
    
    select2 = {
        'entities_leads': {
            'items' : entities_items,
            'text': 'name'
        },
        'entities_contracts': {
            'items' : entities_items,
            'text': 'name'
        },
        'product_sub_types':{
            'items': product_sub_types,
            'text': 'name',
            'force_ajax': True
        }
    }

    return render(
        'edit_offers.html',
        select2=select2,
        device_types=device_types,
        product_models_data=product_sub_types, 
        OfferType=OfferType,
        VALID_OFFER_TYPES=VALID_OFFER_TYPES,
        days_of_month=days_of_month,
        entities=OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True)
    )
