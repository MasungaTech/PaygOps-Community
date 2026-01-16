from flask import flash, redirect, request, url_for
from flask_login import current_user, login_required
from pony.orm import db_session

from constants import (CREATE_STOCK_MOVE_PERMS, DEVICES_VIEWS,
                       VIEW_GLOBAL_STOCK_PERMS, VIEW_STOCK_PERMS)
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from core_system.users.services.user_getter_service import User
from payg_loan_system.devices.device_api.device_api_service import \
    DeviceAPIService
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from payg_loan_system.devices.services.device_tag_getter import \
    DeviceTagService
from shared.helpers.authorizer import authorizer
from shared.helpers.pagination import Pagination
from shared.helpers.select2 import render
from stock_management_system.services.product_sub_type_service import \
    ProductSubTypeService
from stock_management_system.services.quantity_stock_movement_service import \
    QuantityStockMovementService
from stock_management_system.services.stock_count_service import \
    StockCountService
from stock_management_system.services.stock_item_filter_service import \
    StockItemFilterService
from stock_management_system.services.stock_item_getter_service import \
    StockItemGetterService
from stock_management_system.services.stock_item_sort_service import \
    StockItemSorter
from stock_management_system.services.stock_movement_filter_service import \
    StockMovementFilterService
from stock_management_system.services.stock_movement_getter_service import \
    StockMovementGetterService
from stock_management_system.services.stock_movement_sort_service import (
    QuantityStockMovementSorter, StockMovementSorter)
from stock_management_system.stock_status import StockStatus, StockMovementStatus

from . import stock_management


@stock_management.route('/', methods=['GET', 'POST'])
@login_required
@authorizer(VIEW_STOCK_PERMS+VIEW_GLOBAL_STOCK_PERMS)
@db_session
def stock_list():

    pagination = Pagination.generate(request, default_sort='serial_number:desc')

    view = request.args.get('view', 'all')
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(
        current_user, request.args, "entity_id", strict=False
    )

    stock_items = StockItemGetterService.get_from_filtered_view(
        current_user,
        view=view,
        entity=entity,
    )

    tags = request.args.get('tags', '')
    tags = DeviceTagService.extract_tags(tags, current_user)
    stock_items = StockItemFilterService.filter_by_tags(stock_items, tags)

    param_list = [
        'product_type', 'search', 'status', 'stock_user',
        'stock_client', 'stock_shop', 'product_sub_type'
    ]
    params = {k: request.args.get(k, '') for k in param_list}
    stock_items = StockItemFilterService.filter(stock_items, **params)

    pagination.objects = StockItemSorter.sort(stock_items, pagination.sort)

    product_types = DeviceAPIService.get_device_types_and_type_names()
    shops = OperationalEntitiesGetterService.get_list(current_user, stock_enabled=True)
    # here we filter by device_type and not product_type on purpose,
    # device_type is coming from the select2 (to filter in the dropdown
    # only models of one specific type) and product_type is coming from
    # the filters to show only devices of that type
    product_sub_types = ProductSubTypeService.get_filtered_objects(
        current_user, device_type=request.args.get('device_type')
    )
    selected_pst = ProductSubType.get(lambda pst: pst.id == (params['product_sub_type'] or -1))

    select2 = {
        'shoplist': {
            'items': shops,
            'selected': request.args.get('stock_shop'),
            'text': 'name'
        },
        'product_sub_types':{
            'items': product_sub_types,
            'selected': selected_pst,
            'force_ajax': True,
            'text': 'name'
        }
    }

    return render(
        'stock_list.html',
        select2=select2,
        product_types=product_types,
        statuses=StockStatus,
        shoplist=shops,
        pagination=pagination,
        view=view,
        views=DEVICES_VIEWS,
        entity=entity,
        tags=tags,
        product_models_data=product_sub_types,
        **params
    )


@stock_management.route('/movements/')
@login_required
@authorizer(VIEW_STOCK_PERMS+VIEW_GLOBAL_STOCK_PERMS)
@db_session
def stock_movements():

    pagination_serialized = Pagination.generate(request, default_sort='date:desc')
    pagination_quantity = Pagination.generate(request, default_sort='date:desc')

    view = request.args.get('view', 'all')
    entity = OperationalEntitiesGetterService.extract_from_user_and_id(
        current_user, request.args, "entity_id", strict=False
    )

    serialized_movements = StockMovementGetterService.get_from_filtered_view(
        current_user,
        view,
        entity=entity
    )

    quantity_movements = QuantityStockMovementService.get_list(
        current_user
    )

    param_list = ['begin_date', 'end_date', 'search', 'origin_status', 'origin_user',
                  'origin_client', 'origin_shop', 'destination_status', 'accepted_status', 'destination_user',
                  'destination_client', 'destination_shop', 'product_type', 'product_subtype', 'my_pending_stock_only']
    params = {k: request.args.get(k, '') for k in param_list}

    serialized_movements = StockMovementFilterService.filter(serialized_movements, **params)
    quantity_movements = StockMovementFilterService.filter_quantity(quantity_movements, **params)

    serialized_movements_count = StockMovementFilterService.get_pending_serialized_stock_movement_count(serialized_movements)
    quantity_movements_count = StockMovementFilterService.get_pending_quantity_stock_movement_count(quantity_movements)

    pagination_serialized.objects = StockMovementSorter.sort(
        serialized_movements, pagination_serialized.sort
    )
    pagination_quantity.objects = QuantityStockMovementSorter.sort(
        quantity_movements, pagination_quantity.sort
    )

    can_add = current_user.can_access_in_scope(CREATE_STOCK_MOVE_PERMS)
    shops = OperationalEntitiesGetterService.get_list(current_user, stock_enabled=True)

    product_subtypes = ProductSubTypeService.get_filtered_objects(
        current_user, device_type=request.args.get('device_type')
    ).order_by(lambda pst:pst.id)
    product_types = DeviceAPIService.get_device_types_and_type_names()
    selected_pst = ProductSubType.get(lambda pst: pst.id == (params.get('product_subtype') or -1))

    select2 = {
        'shoplist_orig': {
            'items': shops,
            'text': 'name',
            'selected': request.args.get('origin_shop'),
            'force_ajax': True
        },
        'shoplist_dest': {
            'items': shops,
            'text': 'name',
            'selected': request.args.get('destination_shop'),
            'force_ajax': True
        },
         'product_subtypes': {
            'items': product_subtypes,
            'selected': selected_pst,
            'force_ajax': True,
            'text': 'name'
        }
    }

    return render(
        'stock_movements.html',
        select2=select2,
        view=view,
        views=DEVICES_VIEWS,
        entity=entity,
        statuses=StockStatus,
        stock_movement_statuses=StockMovementStatus,
        pagination_serialized=pagination_serialized,
        pagination_quantity=pagination_quantity,
        serialized_movements_count=serialized_movements_count,
        quantity_movements_count=quantity_movements_count,
        can_add=can_add,
        product_models_data=product_subtypes,
        product_types=product_types,
        **params
    )


@stock_management.route('/movements/add', methods=['GET', 'POST'])
@login_required
@authorizer(CREATE_STOCK_MOVE_PERMS)
@db_session
def add_movements():
    has_permission = False
    destinations = {}
    def _update(status):
        destinations.update({status: StockStatus.to_human(status)})

    select2_source = request.args.get('source')
    select2 = {}

    if not select2_source or select2_source == 'device_code_adder':
        all_items = StockItemGetterService.get_movable_items(current_user)
        select2.update({
            'device_code_adder': {
                'items': all_items,
                'id': 'id',
                'text': 'composed_serial'
            }
        })
        if select2_source:
            return render(select2=select2)

    if not select2_source or select2_source == 'shops':
        shops = []
        if current_user.can_access_in_any('ToInStockMoveStock'):
            has_permission = True
            _update('in_stock')
            shops = current_user.reload().get_entities_with_permission('ToInStockMoveStock')
            shops = shops.filter(lambda s: s.level != -1)
        shops = OperationalEntitiesGetterService.stock_enabled_filter(shops, enabled=True)
        select2.update({
            'shops': {
                'items': shops,
                'text': 'name'
            }
        })
        if select2_source:
            return render(select2=select2)

    if not select2_source or select2_source == 'users':
        users = []
        if current_user.can_access_in_any('ToUsersMoveStock'):
            has_permission = True
            _update('with_user')
            users = User.select().filter(
                lambda u: u.shop in current_user.reload()
                .get_entities_with_permission('ToUsersMoveStock')
            )
        elif current_user.can_access_in_any('ToWithMeMoveStock'):
            has_permission = True
            _update('with_user')
            users = User.select().filter(lambda u: u == current_user)
        select2.update({
            'users': {
                'items': users,
                'text': 'full_name'
            }
        })
        if select2_source:
            return render(select2=select2)


    if not select2_source or select2_source == 'product_subtypes':
        product_subtypes = ProductSubTypeService.get_filtered_objects(
            current_user, device_type=request.args.get('device_type'),
            is_serialized=False
        ).order_by(lambda pst: pst.id)
        select2.update({
            'product_subtypes': {
                'items': product_subtypes,
                'text': 'name',
                'force_ajax': True
            }
        })
        if select2_source:
            return render(select2=select2)

    if current_user.can_access('ToOrphanedMoveStock'):
        has_permission = True
        _update('orphaned')
        _update('lost')

    if not all_items.count() or not has_permission:
        flash(
            '''There is no Stock Item available to move manually.
            Check Permissions and location of items.'''
        )
        return redirect(url_for('.stock_movements'))

    product_types = DeviceAPIService.get_device_types_and_type_names()
    origin_status = 'Orphaned'

    return render('add_movements.html',
                  statuses=StockStatus,
                  shops=shops,
                  users=users,
                  destinations=destinations,
                  product_subtypes=product_subtypes,
                  product_types=product_types,
                  origin_status=origin_status,
                  select2=select2)

@stock_management.route('/stock_count/', methods=['GET', 'POST'])
@login_required
@authorizer(CREATE_STOCK_MOVE_PERMS+['ManageQuantityViewStock'])
@db_session
def stock_count():

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(
        current_user, request.args, "entity_id", strict=False
    )

    select2 = {
        'entities': {
            'items': OperationalEntitiesGetterService.get_list(
                current_user, only_hierarchical=True
            ),
            'text': 'name',
            'selected': entity
        }
    }

    if request.args.get('source'):
        return render(select2=select2)

    search = request.args.get('search')
    product_subtypes = ProductSubType.select()
    if search:
        product_subtypes = product_subtypes.filter(lambda p: search.lower() in p.name.lower())
    psts = [None] + product_subtypes[:]

    if entity:
        count = [(
            pst,
            StockCountService.get_count(pst, entity, StockStatus.in_stock),
            StockCountService.get_count(pst, entity, StockStatus.in_stock, children=True),
            StockCountService.get_count(pst, entity, StockStatus.with_user),
            StockCountService.get_count(pst, entity, StockStatus.with_user, children=True),
            StockCountService.get_count(pst, entity, StockStatus.installed),
            StockCountService.get_count(pst, entity, StockStatus.installed, children=True)
        ) for pst in psts]
    else:
        count = [(
            pst,
            StockCountService.get_total_count(pst, StockStatus.in_stock),
            StockCountService.get_total_count(pst, StockStatus.with_user),
            StockCountService.get_total_count(pst, StockStatus.installed),
            StockCountService.get_total_count(pst, StockStatus.orphaned),
            StockCountService.get_total_count(pst, StockStatus.lost),
        ) for pst in psts]

    return render(
        'stock_count.html', 
        entity=entity,
        stock_count=count,
        search=search,
        product_subtypes=[(pst.id, pst.name) for pst in psts if pst and not pst.is_serialized],
        select2=select2
    )
