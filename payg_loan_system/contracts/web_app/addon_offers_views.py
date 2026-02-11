from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from flask_login import login_required, current_user
from payg_loan_system.contracts.models.addons_model import AddOnLoanExtensionMode, AddOnOffer, AddOnType
from flask import abort, render_template, request
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from stock_management_system.services.product_sub_type_service import ProductSubTypeService
from . import contract
from shared.helpers.select2 import render
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.contracts.services.addon_category_service import AddonCategoryService


@contract.route('/addons_offers/<int:offer_id>/add_version', methods=['GET'])
@login_required
@authorizer('AddAddonOffers')
@db_session
def add_addon_offer_version(offer_id):
    offer = AddonOfferGetterService.get_from_user_and_id(current_user, offer_id, strict=True, main_resource=True)
    if offer.is_system():
        abort(404)
    return render_template(
        'add_addon_offer_version.html',
        AddOnType=AddOnType,
        offer=offer
    )


@contract.route('/addons_offers/add', methods=['GET'])
@login_required
@authorizer('AddAddonOffers')
@db_session
def add_addon_offer():
    
    entities = OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True)
    based_on = AddonOfferGetterService.extract_from_user_and_id(current_user, request.args, "based_on_id", strict=False)
    device_types = DeviceAPIService.get_device_types_and_type_names(include_data_attributes=True, exclude_time_units=True)

    offers = AddonOfferGetterService.get_list(current_user).order_by(AddOnOffer.code)

    product_sub_types = ProductSubTypeService.get_list(current_user, device_type=request.args.get('device_type'))

    select2 = {
        'product_sub_types': {
            'items': product_sub_types,
            'text': 'name',
            'force_ajax': True
        },
        'entities_leads': {
            'items' : OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True),
            'text': 'name'
        },
        'entities_contracts': {
            'items' : OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True),
            'text': 'name'
        }
    }
    if 'source' in request.args and request.args['source'] in ['product_model_selector']:
        return render(None, select2=select2)
    
    category = AddonCategoryService.extract_from_user_and_id(current_user, request.args, 'category')
    if category:
        offers = offers.filter(lambda o: o in category.covered_offers)
        bundles = bundles.filter(lambda o: o in category.covered_bundles)

    return render(
        'edit_addon_offer.html',
        select2=select2,
        categories={c.name:c.name for c in AddonCategoryService.get_list(current_user)},
        AddOnType=AddOnType,
        addon_types={c: AddOnType.to_human(c) for c in AddOnType.to_list() if c not in AddOnType._NO_VALUE_TYPES},
        loan_modes={c: AddOnLoanExtensionMode.to_human(c) for c in AddOnLoanExtensionMode.to_list()},
        entities=entities,
        based_on=based_on,
        device_types=device_types,
        product_models_data=product_sub_types,
    )


@contract.route('/addons_offers/<int:offer_id>', methods=['GET'])
@login_required
@authorizer('ViewAddonOffers')
@db_session
def view_addon_offer(offer_id):

    offer = AddonOfferGetterService.get_from_user_and_id(current_user, offer_id, strict=True, main_resource=True)
    return render_template('view_addon_offer.html', offer=offer, AddOnType=AddOnType)



@contract.route('/addons_offers/<int:offer_id>/edit', methods=['GET'])
@login_required
@authorizer('EditAddonOffers')
@db_session
def edit_addon_offer(offer_id):

    offer = AddonOfferGetterService.get_from_user_and_id(current_user, offer_id, strict=True, main_resource=True)
    based_on = AddonOfferGetterService.extract_from_user_and_id(current_user, request.args, "based_on_id", strict=False)
    device_types = DeviceAPIService.get_device_types_and_type_names(include_data_attributes=True, exclude_time_units=True)
    product_sub_types = ProductSubTypeService.get_filtered_objects(current_user, device_type=request.args.get('device_type'))

    select2 = {
        'entities_leads': {
            'selected': [(e.id, e.name) for e in offer.entities_allowed_for_leads],
            'items' : OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True),
            'text': 'name'
        },
        'entities_contracts': {
            'selected': [(e.id, e.name) for e in offer.entities_allowed_for_contracts],
            'items' : OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True),
            'text': 'name'
        },
        'product_sub_types':{
            'items': product_sub_types,
            'selected': offer.product_sub_type if offer.product_sub_type else None,
            'text': 'name',
            'force_ajax': True
        }
    }

    entities_allowed_for_leads = [e.id for e in offer.entities_allowed_for_leads]
    entities_allowed_for_contracts = [e.id for e in offer.entities_allowed_for_contracts]

    return render(
        'edit_addon_offer.html',
        offer=offer,
        entities_allowed_for_leads=entities_allowed_for_leads,
        entities_allowed_for_contracts=entities_allowed_for_contracts,
        categories=AddonCategoryService.get_list(current_user).filter(lambda c: not c.parent),
        AddOnType=AddOnType,
        addon_types=[(c, AddOnType.to_human(c)) for c in AddOnType.to_list() if offer.type == c or c not in AddOnType._NO_VALUE_TYPES],
        loan_modes={c: AddOnLoanExtensionMode.to_human(c) for c in AddOnLoanExtensionMode.to_list()},
        select2=select2,
        entities=OperationalEntitiesGetterService.get_list(current_user, only_hierarchical=True),
        based_on=based_on,
        device_types=device_types,
        product_models_data=product_sub_types,
    )
