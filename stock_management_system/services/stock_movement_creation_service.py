from datetime import datetime

from flask_login import current_user
from pony.orm import flush, select

from core_system.core_entities import db
from core_system.operational_entities.models import OperationalEntity
from core_system.users.models.user_model import User
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.logger.loggers import Error, LogAPI
from shared.services.base_service import BaseService
from shared.services.settings_service import SettingsService
from stock_management_system.models import StockItem, StockMovement
from stock_management_system.services.permission_helpers import StockMovementPermissionHelper
from stock_management_system.services.stock_item_getter_service import \
    StockItemGetterService
from stock_management_system.stock_status import StockMovementStatus, StockStatus


class StockMovementCreationService(BaseService):

    WARNINGS = {
        'MANUAL_STOCK_INSTALLED': 'Stock Item {serial_number} cannot be manually moved from a client.',
        'STOCK_ITEM_RESERVED': 'Stock Item {serial_number} is reserved and cannot be moved, review movements pending approval.',
        'MANUAL_STOCK_TO_CLIENT': 'Stock Item {serial_number} cannot be manually moved to a client.',
        'USER_NOT_ALLOWED': 'Permissions not enough to move the Stock Item {serial_number} to this destination.',
        'MOVEMENT_TO_SAME_STATUS': 'Stock Item {serial_number} is already in the location specified.'
    }

    @classmethod
    def _add_from_data_and_user(cls, data, user, **kwargs):
        user = user.reload()
        # No need to check permissions here as they are checked in the create function
        stock_item_ids = data.get('stock_item_ids', [])
        multiple = True
        if not stock_item_ids and data.get('stock_item_id'):
            multiple = False
            stock_item_ids = [data.get('stock_item_id')]

        serial_number = data.get('serial_number')
        stock_items = select(s for s in StockItem if s.id in stock_item_ids or s.device.composed_serial == serial_number)
        destination_status = data.get('destination_status')
        destination_entity = data.get('destination_entity_id')
        if destination_entity:
            destination_entity = OperationalEntity.get(id=destination_entity)
        destination_user = data.get('destination_user_id')
        if destination_user:
            destination_user = User.get(id=destination_user)


        response, _  = cls.create(
            stock_items=stock_items,
            destination_status=destination_status,
            destination_user=destination_user,
            destination_entity=destination_entity,
            user=user,
            note=data.get('note') or '',
            manual=data.get('manual', True)
        )
        return response if multiple else response[0]

    @classmethod
    def create(cls, stock_items, destination_status, user=None, date=None, note='',
        destination_user=None, destination_client=None, destination_entity=None,
        manual=True, suppress_errors=False):

        if date is None:
            date = datetime.now()
        elif manual:
            raise Exception('Date cannot be set in manual mode.')

        if user is None and current_user:
            uid = current_user.id
            user = db.User[uid]

        if isinstance(stock_items, StockItem):
            stock_items = [stock_items]

        approval_status = StockMovementStatus.accepted
        acknowledge_transfer = SettingsService.get_setting('AllowUsersToReceiveStock')
        if acknowledge_transfer and destination_user and destination_user != user:
            approval_status = StockMovementStatus.pending

        assert manual or approval_status != StockMovementStatus.pending, \
            'Automatic movement set as pending'

        if destination_entity:
            # The or is only used when in the testing pipeline to have
            # a default since the setter is complex
            levels_enabled = SettingsService.get_setting(
                'OperationalEntitiesInventory'
            ) or [True, True, True, False, False]
            level = destination_entity.level
            if not levels_enabled[level]:
                raise Error(f'Level {level} is not enabled for inventory management')

        warnings = []
        moves = []
        for stock_item in stock_items:
            if manual:
                if not stock_item.last_movement:
                    raise Exception(
                        f'StockItem[{stock_item.id}] cannot be manually moved '
                        + 'without an initial movement of creation (usually to orphaned).'
                    )
                if stock_item.status == StockStatus.installed:
                    cls.add_warning(warnings, 'MANUAL_STOCK_INSTALLED', stock_item, suppress_errors)
                    continue
                if stock_item.reserved:
                    cls.add_warning(warnings, 'STOCK_ITEM_RESERVED', stock_item, suppress_errors)
                    continue
                if destination_status == StockStatus.installed:
                    cls.add_warning(warnings, 'MANUAL_STOCK_TO_CLIENT', stock_item, suppress_errors)
                    continue
                destination = {
                    'status': destination_status,
                    'user': destination_user,
                    'shop': destination_entity
                }
                if user and not StockMovementPermissionHelper.user_can_move(
                    stock_item, destination, user
                ):
                    cls.add_warning(warnings, 'USER_NOT_ALLOWED', stock_item, suppress_errors)
                    continue
            if (stock_item.last_movement
                    and destination_status == stock_item.status
                    and destination_user == stock_item.user
                    and destination_client == stock_item.client
                    and destination_entity == stock_item.shop):
                cls.add_warning(warnings, 'MOVEMENT_TO_SAME_STATUS', stock_item, suppress_errors)
                continue

            move = StockMovement(
                stock_item=stock_item,
                destination_status=destination_status,
                date=date,
                note=note,
                user=user,
                destination_user=destination_user,
                destination_client=destination_client,
                destination_entity=destination_entity,
                approval_status=approval_status,
                product_sub_type=stock_item.device.product_sub_type.id if stock_item.device and stock_item.device.product_sub_type else None
            )
            flush()
            add_hook_after_commit(db, 'new_stock_movement', move.get_serialized_object())
            moves.append(move)

        if warnings and not manual:
            LogAPI.Warning(repr(warnings))

        return moves, warnings

    @classmethod
    def user_can_make_action(cls, stock_item, user):
        if (StockItemGetterService.user_can_see(stock_item, user) or
                user.can_access('MakeOnStockOutsideViewActions')):
            return True

    @classmethod
    def _item_related_to_shop(cls, stock_item, shop):
        return cls._related_to_shop(stock_item.shop, stock_item.user, shop)

    @classmethod
    def _destination_related_to_shop(cls, destination, shop):
        return cls._related_to_shop(destination['shop'], destination['user'], shop)

    @staticmethod
    def _related_to_shop(shop, user, target_shop):
        if shop and shop != target_shop:
            return False
        if user and user.shop != target_shop:
            return False
        if not (shop or user):
            return False
        return True

    @classmethod
    def add_warning(cls, warnings, code, item, suppress_errors):
        msg = cls.WARNINGS[code].format(serial_number=item.device.composed_serial)
        if not suppress_errors:
            raise Error(msg, code=code, stock_item=item.get_serialized_object())
        warnings.append({
            'code': code,
            'stock_item': item,
            'msg': msg
        })
