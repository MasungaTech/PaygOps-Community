import json
from datetime import datetime, timedelta

from flask import flash, redirect, request, url_for
from flask_login import current_user, login_required
from pony.orm import db_session, select

from constants import ADDONS_STATUSES_NAMES
from core_system.portfolios.services.portfolio_getter_service import \
    PortfolioGetterService
from payg_loan_system.contracts.models.addons_model import (
    AddOnLoanExtensionMode, AddOnOffer, AddOnOfferVersion, AddOnType)
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.services.addon_bundle_list_service import \
    AddonBundleListService
from payg_loan_system.contracts.services.addon_category_service import \
    AddonCategoryService
from payg_loan_system.contracts.services.addon_list_service import \
    AddonListService
from payg_loan_system.contracts.services.addon_sorter import AddonSorter
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import \
    AddonOfferGetterService
from payg_loan_system.contracts.services.contract_getter_service import \
    ContractGetterService
from payg_loan_system.contracts.services.contract_graph_service import \
    IndividualContractGraphService
from payg_loan_system.devices.device_list_service import DeviceListService
from payg_loan_system.offers.models import OfferType
from shared.helpers.authorizer import authorizer
from shared.helpers.clock import Clock
from shared.helpers.form_helpers import dateTimePickerToStandard
from shared.helpers.pagination import Pagination
from shared.helpers.select2 import render
from shared.services.settings_service import SettingsService

from . import contract as contract_blueprint


@contract_blueprint.route('/<contract_reference>/check_cache', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@db_session
def check_contract_cache(contract_reference):
    contract = ContractGetterService.get_from_user_and_properties(
        current_user, reference=contract_reference, strict=True, main_resource=True
    )
    from payg_loan_system.contracts.services.contract_cache_service import \
        ContractCacheService
    ContractCacheService.check_cache_accuracy(contract, fix_if_needed=True)
    return 'OK'


@contract_blueprint.route('/<contract_reference>', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@db_session
def view_contract(contract_reference):

    contract = ContractGetterService.get_from_user_and_properties(
        current_user, reference=contract_reference
    )

    if not contract:
        flash('This contract does not exists. ')
        return redirect(url_for('.list_contracts'))

    if contract.usage_based:
        graph_data_2 = IndividualContractGraphService.get_contract_timeline_graph_data_for_usage_based(contract)
    else:
        graph_data_2 = IndividualContractGraphService.get_contract_timeline_graph_data(contract)

    addon_fields = ['reference', 'offer', 'quantity_sold', 'total_addon_value',
                    'time_created', 'sold_by', 'status', 'payment_source']
    addon_eligible = contract.status != ContractStatus.defaulted
    addon_offer = AddonOfferGetterService.extract_from_user_and_id(
        current_user, request.args, "offer_id", strict=False
    )
    offer_type = request.args.get('offer_type')
    offer_id = request.args.get('offer_id')
    search = request.args.get('search')

    default_from = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
    from_date_str = request.args.get('from_date', default_from)
    to_date_str = request.args.get(
        'to_date', (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    )
    from_date = dateTimePickerToStandard(from_date_str)
    from_date_utc = Clock.localize_to_utc(from_date)
    to_date = dateTimePickerToStandard(to_date_str, '23:59')
    to_date_utc = Clock.localize_to_utc(to_date)

    paginations = {}
    
    if not SettingsService.get_setting('FeatureToggles').get('OffTaking'):
        ADDONS_STATUSES_NAMES.pop('offtaking', None)

        
    for tab in ADDONS_STATUSES_NAMES:
        paginations[tab] = Pagination.generate(request, tab=tab, default_sort='reference')
        addons = AddonListService.get_from_filtered_view(
            current_user.reload(),
            contract_reference=contract.reference,
            status=tab,
            offer_type=offer_type,
            offer_id=offer_id,
            from_date=from_date_utc,
            to_date=to_date_utc,
            search=search
        )
        paginations[tab].objects = AddonSorter.sort(addons, paginations[tab].sort, 'reference')

    all_addons = AddonListService.get_from_filtered_view(
        current_user, contract_reference=contract.reference
    )
    offer_versions = select(addon.offer_version for addon in all_addons) # to fix
    offers = select(v.offer for v in offer_versions) # to fix
    devices = DeviceListService.get_non_used_devices_for_user_list(current_user, offer=contract.offer)
    select2 = {
        'offer_types': {
            'items':{t: t for t in AddOnType.to_list()},
            'raw_format': True,
        },
        'addon_offers': {
            'items': offers,
            'text': 'name'
        },
        'portfolios': {
            'items': PortfolioGetterService.get_filtered_objects(current_user=current_user),
            'text': 'name',
            'selected': contract.portfolio.id if contract.portfolio else None
        },
         'devices':{
            'items': devices,
            'id': 'composed_serial',
            'text': 'composed_serial',
            'force_ajax': True 
        }
    }
    formattedCustomButtons = []
    settings = SettingsService.get_setting('customButtonConfiguration')
    if settings:
        for button in settings:
            if button.get('TargetPage') == 'contract' and button.get('TargetUrl'):
                button['TargetUrl'] = button['TargetUrl'].format(
                    contract_id=contract.id,
                    contract_reference=contract.reference,
                    custom_id=contract.client.person.custom_id or '',
                    contract_phone_number=contract.person.contactPhone.number if contract.person.contactPhone else '',
                    contract_serial_number=contract.linked_device.composed_serial if contract.linked_device else '',
                    user_id=current_user.id,
                    user_name=current_user.full_name,
                    client_id=contract.client.id,
                    name=contract.client.full_name,
                    client_phone_number=contract.client.person.contactPhone.number if contract.client.person.contactPhone else '',
                )
                formattedCustomButtons.append(button)
    return render(
        'view_contract.html',
        contract=contract,
        graph_data_2=graph_data_2,
        addon_fields=addon_fields,
        tabs=ADDONS_STATUSES_NAMES,
        paginations=paginations,
        addon_eligible=addon_eligible,
        OfferType=OfferType,
        AddOnType=AddOnType,
        AddOnLoanExtensionMode=AddOnLoanExtensionMode,
        offer_type=offer_type,
        addon_offer=addon_offer,
        offer_id=addon_offer.id if addon_offer else None,
        select2=select2,
        from_date=from_date,
        to_date=to_date,
        search=search,
        formattedCustomButtons=formattedCustomButtons,
        active_tab=request.args.get('tab', 'all'),
        ContractStatus=ContractStatus,
    )

@contract_blueprint.route('/<contract_reference>/sell_addon', methods=['GET', 'POST'])
@login_required
@authorizer('AddToContractAddOns')
@db_session
def add_contract_addon(contract_reference):

    contract = ContractGetterService.get_from_user_and_properties(
        current_user, reference=contract_reference
    )
    if not contract:
        flash('This contract does not exists. ')
        return redirect(url_for('.list_contracts'))
    if contract.status == ContractStatus.defaulted:
        flash('The contract is not eligible to be sold an addon since it is defaulted')
        return redirect(url_for('contract.view_contract', contract_reference=contract.reference))

    offers = AddonOfferGetterService.get_list(
        current_user, for_contract=contract
    ).order_by(AddOnOffer.code)
    offer_versions_data = AddonOfferGetterService.formatted_addon_offer_list(
        offers, for_contract=contract
    )
    bundles = AddonBundleListService.get_list(
        current_user, for_offer=contract.offer, for_entity_contract=contract.client.person.village
    )

    category = AddonCategoryService.extract_from_user_and_id(current_user, request.args, 'category')
    if category:
        offers = offers.filter(lambda o: o in category.covered_offers)
        bundles = bundles.filter(lambda o: o in category.covered_bundles)

    bundles_available = bundles.exists()
    categories_available = AddonCategoryService.get_list(current_user).exists()

    add_offer_version = AddOnOfferVersion.get(id=request.args.get('add_on_offer', -1))
    devices = DeviceListService.get_non_used_devices_for_user_list(
        current_user, add_on_offer=add_offer_version.offer if add_offer_version else None
    )

    select2 = {
        'offer_version_id': {
            'items': offers,
            'id': 'version_for_sales_id',
            'text': 'name_and_version_for_sales',
            'search_field': 'name',
            'force_ajax': True
        },
        'bundle_id': {
            'items': bundles,
            'text': 'name',
            'force_ajax': True
        },
        'add_on_devices': {
            'items': devices,
            'text': 'composed_serial',
            'force_ajax': True,
            'id': 'composed_serial'
        }
    }

    return render(
        'add_contract_addon.html',
        contract=contract,
        offers=offers,
        AddOnLoanExtensionMode=AddOnLoanExtensionMode,
        loan_modes={
            c: AddOnLoanExtensionMode.to_human(c) for c in AddOnLoanExtensionMode.to_list()
        },
        offers_data=json.dumps(offer_versions_data),
        bundles_available=bundles_available,
        categories_available=categories_available,
        select2=select2
    )
