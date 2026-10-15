from payg_loan_system.contracts.services.addon_bundle_list_service import AddonBundleListService
from payg_loan_system.contracts.services.addon_offer_sorter import AddonOfferSorter
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from payg_loan_system.contracts.services.addon_category_service import AddonCategoryService
from flask_login import login_required, current_user
from flask import render_template, request
from payg_loan_system.contracts.models.addons_model import AddOnLoanExtensionMode, AddOnOffer, AddOnType
from payg_loan_system.contracts.models.addon_bundle_model import ContractAddOnBundle
from payg_loan_system.contracts.services.bundle_sorter import AddonBundleSorter
from shared.helpers.authorizer import authorizer
from pony.orm import db_session
import json
from shared.helpers.pagination import Pagination
from . import contract
from shared.helpers.select2 import render
from shared.services.translation_service import TranslationService


@contract.route('/addons_configuration', methods=['GET', 'POST'])
@login_required
@authorizer('ViewAddonOffers')
@db_session
def addons_configuration():

    search_offers = request.form.get('search', request.args.get('search', ''))
    active_filter = request.form.get('active_filter', request.args.get('active_filter', 'default'))
    purchasing_addons_filter = request.form.get('purchasing_addons_filter', request.args.get('purchasing_addons_filter', 'default'))
    search_bundles = request.form.get('search_bundles', request.args.get('search_bundles', ''))

    category_name = request.form.get('category', request.args.get('category', ''))
    category = AddonCategoryService.get_from_user_and_properties(current_user, name=category_name) if category_name else None

    offers = AddonOfferGetterService.get_list(current_user).order_by(AddOnOffer.id).prefetch(AddOnOffer.versions)
    bundles = AddonBundleListService.get_list(current_user).order_by(ContractAddOnBundle.id)


    if active_filter in ['default', 'active']:
        active_filter = 'active'
        offers = offers.filter(lambda offer: offer.versions.filter(lambda ov: ov.available_for_registration).count() > 0 or offer.versions.filter(lambda ov: ov.available_for_sales).count() > 0)
    if active_filter == 'inactive':
        offers = offers.filter(lambda offer: not offer.versions.select(lambda o: o.available_for_registration) and not offer.versions.select(lambda o: o.available_for_sales))

    if purchasing_addons_filter == 'regular':
        offers = offers.filter(lambda offer: not offer.versions.select(lambda o: o.offer.purchasing_addon))

    if purchasing_addons_filter == 'purchasing_addons':
        offers = offers.filter(lambda offer: offer.versions.offer.purchasing_addon)

    if search_offers != '':
        offers = offers.filter(lambda o: search_offers.lower() in (o.name + ' ' + o.code).lower())
    
    if category:
        offers = offers.filter(lambda o: o in category.covered_offers)

    if search_bundles != '':
        bundles = bundles.filter(lambda b: search_bundles.lower() in (b.name).lower())

    categories = AddonCategoryService.get_list(current_user).filter(lambda c: not c.parent)

    offers_pagination = Pagination.generate(request, tab='offers', default_sort='id:desc')
    offers_pagination.objects = AddonOfferSorter.sort(offers, offers_pagination.sort)

    bundles_pagination = Pagination.generate(request, tab='bundles', default_sort='id:desc')
    bundles_pagination.objects = AddonBundleSorter.sort(bundles, bundles_pagination.sort)

    return render_template(
        'addons_configuration.html',
        AddOnType=AddOnType,
        offers_pagination=offers_pagination,
        bundles_pagination=bundles_pagination,
        active_filter=active_filter,
        search_offers=search_offers,
        search_bundles=search_bundles,
        categories=categories,
        purchasing_addons_filter=purchasing_addons_filter,
        selected_category=category
    )


def category_has_children(children, excluded, with_results=False):
    if with_results == 'offers':
        for c in children:
            if (c.covered_offers.count() != 0) and c.name.lower() not in excluded:
                return True
    elif with_results == 'bundles':
        for c in children:
            if (c.covered_bundles.count() != 0) and c.name.lower() not in excluded:
                return True
    else:
        for c in children:
            if c.name.lower() not in excluded:
                return True
    return False


@contract.route('/addons_categories_data', methods=['GET'], defaults={'parent_id': None})
@contract.route('/addons_categories_data/<int:parent_id>', methods=['GET'])
@login_required
@authorizer('ViewAddonOffers')
@db_session
def view_addons_categories_data(parent_id):
    parent = AddonCategoryService.get_from_user_and_id(current_user, parent_id) if parent_id else None
    excluded = request.args.get('excluded', "").lower().split(',')
    with_results = request.args.get('with_results' ,"").lower()
    term = request.args.get('q', request.args.get('term', '')).lower()
    items = AddonCategoryService.get_list(current_user, parent=parent, search=term, excluded=excluded, with_results=with_results)[:]

    results = {
        'results': []
    }
    for item in items:
        has_children = category_has_children(item.children, excluded, with_results)
        results['results'].append({
            'id': item.id,
            'text': item.name,
            'data': {
                'children': has_children,
                'breadcrumbs': item.get_breadcrumbs_text()
            }
        })
    return json.dumps(results)


@contract.route('/addons_categories/<int:category_id>', methods=['GET'])
@login_required
@authorizer('ViewAddonOffers')
@db_session
def view_addon_category(category_id):

    category = AddonCategoryService.get_from_user_and_id(current_user, category_id, strict=True, main_resource=True)
    return render_template('view_addon_category.html', category=category)


@contract.route('/addons_bundles/<int:bundle_id>', methods=['GET'])
@login_required
@authorizer('EditAddonOffers')
@db_session
def view_addon_bundle(bundle_id):

    bundle = AddonBundleListService.get_from_user_and_id(current_user, bundle_id, strict=True, main_resource=True)

    offers = AddonOfferGetterService.get_list(current_user).order_by(AddOnOffer.code)
    offers_data_full = AddonOfferGetterService.formatted_addon_offer_list(offers, for_bundle=True)
    offers_data_select = {k: v['name'] for k,v in offers_data_full.items()}

    category_id = request.args.get('category')
    if category_id:
        category = AddonCategoryService.get_from_user_and_id(current_user, category_id)
        if category:
            offers = offers.filter(lambda o: o in category.covered_offers)

    select2 = {
        'offer_id_selector': {
            'items': offers,
            'text': 'name'
        }
    }

    categories_available = AddonCategoryService.get_list(current_user).exists()

    return render(
        'view_addon_bundle.html',
        addon_offers=offers_data_select,
        offers_data=json.dumps(offers_data_full),
        bundle=bundle,
        AddOnType=AddOnType,
        AddOnLoanExtensionMode=AddOnLoanExtensionMode,
        loan_modes={c: AddOnLoanExtensionMode.to_human(c) for c in AddOnLoanExtensionMode.to_list()},
        categories_available=categories_available,
        select2=select2
    )
