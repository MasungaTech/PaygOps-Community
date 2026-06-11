from shared.services.base_getter_service import BaseGetterService
from stock_management_system.models import StockMovement
from stock_management_system.services.stock_item_getter_service import StockItemGetterService
import config
from pony.orm import desc

from stock_management_system.services.stock_movement_accept_reject_service import AcceptRejectStockMovementService
from stock_management_system.stock_status import StockMovementStatus

class StockMovementGetterService(BaseGetterService):

    OBJ_NAME = 'Stock Movement'

    @classmethod
    def get_from_filtered_view(cls, user, view=None, entity=None):

        extra = {}
        if view == 'managed_by_me':
            extra = dict(managed_by=user)
        elif view == 'orphaned':
            extra = dict(orphaned=True)
        items = cls.get_list(user, entity=entity, **extra)
        return items

    @classmethod
    def get_filtered_objects(cls, current_user=None, entity=None, orphaned=None, managed_by=None, created_by=None, assigned_to=None, **kwargs):
        movements = StockMovement.select(lambda m: m.previous is not None).order_by(lambda m: desc(m.date))
        items = StockItemGetterService.get_list(current_user, entity=entity, orphaned=orphaned, managed_by=managed_by)
        if config.TEST_MODE:
            items = items[:]
        movements = movements.filter(lambda m: m.stock_item in items)
        if created_by:
            movements = movements.filter(lambda m: m.user == created_by)
        if assigned_to:
            movements = movements.filter(lambda m: m.destination_user == assigned_to)
        return movements

    @classmethod
    def _edit_from_data_and_user(cls, obj, data, user, **kwargs):
        if 'approval_status' in data:
            if data.get('approval_status') == StockMovementStatus.accepted:
                AcceptRejectStockMovementService.accept_movement(obj, user, data.get('note', ''))
            if data.get('approval_status') == StockMovementStatus.rejected:
                AcceptRejectStockMovementService.reject_movement(obj, user, data.get('note', ''))
