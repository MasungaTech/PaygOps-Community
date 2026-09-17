from pony import orm

from core_system.client.services.client_getter_service import \
    ClientGetterService
from core_system.users.services.user_getter_service import UserGetterService
from shared.services.base_getter_service import BaseGetterService
from stock_management_system.models import StockItem
from stock_management_system.stock_status import StockStatus


class StockItemGetterService(BaseGetterService):

    OBJ_NAME = 'Stock Item'

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
    def get_filtered_objects(cls, current_user=None, entity=None, managed_by=None, orphaned=None, for_sale=False, **kwargs):

        items = StockItem.select()
        
        # WARNING: Make sure that any changes you make to this are reflected in the user_can_see() function below

        if not orphaned and not managed_by and not entity and current_user.can_access_in_all('InStockViewStock') \
            and current_user.can_access_in_all('WithUsersViewStock') and current_user.can_access_in_all('WithClientsViewStock') \
            and current_user.can_access('OrphanedViewStock'):
            if for_sale:
                return StockItem.select().filter(lambda i: i.status not in [StockStatus.lost, StockStatus.installed] and not i.reserved)
            return StockItem.select()

        if not for_sale:
            clientsitems = cls._filter_with_user_clients(items, current_user.reload(), managed_by=managed_by, entity=entity)
            clients_ids = orm.select(i.id for i in clientsitems)[:]
        else:
            clients_ids = []

        instockitems = cls._filter_in_stock(items, current_user.reload(), entity=entity, managed_by=managed_by)
        instock_ids = orm.select(i.id for i in instockitems)[:]

        withusersitems = cls._filter_with_users(items, current_user.reload(), entity=entity)
        withusers_ids = orm.select(i.id for i in withusersitems)[:]
        
        myitems = items.filter(lambda i: i.user == current_user) if current_user.can_access('WithMeViewStock') else []  
        myitems_ids = orm.select(i.id for i in myitems)[:] if myitems else []

        orphaned_allowed = current_user.can_access('OrphanedViewStock') and (orphaned or not (entity or managed_by))
        orphaneditems = cls._filter_orphaned(items, for_sale=for_sale) if orphaned_allowed else []
        orphaned_ids = orm.select(i.id for i in orphaneditems)[:] if orphaned_allowed else []
        if orphaned:
            return orphaneditems
        
        all_ids = instock_ids+withusers_ids+myitems_ids+orphaned_ids+clients_ids
        items = items.filter(lambda i: i.id in all_ids)
        return items

    
    @classmethod
    def get_movable_items(cls, current_user):

        # For now we can only move items with devices as we use composed_serial to move.
        # Exclude installed items so they are not offered in the stock movement dropdown;
        # manual moves from a client are rejected by StockMovementCreationService
        # (MANUAL_STOCK_INSTALLED). Reserved items are intentionally left selectable —
        # ticket scope is installed only; STOCK_ITEM_RESERVED still blocks on submit.
        items = orm.select(i for i in StockItem)
        if current_user.can_access_in_all('FromUsersMoveStock') and current_user.can_access('FromWithMeMoveStock') \
            and current_user.can_access_in_all('FromInStockMoveStock') and current_user.can_access('FromOrphanedMoveStock'):
            return items.filter(lambda i: i.device.id != None and i.status not in [StockStatus.installed])

        instockitems_ids = orm.select(i.id for i in cls._filter_in_stock(items, current_user.reload(), to_move=True))[:]
        withusersitems_ids = orm.select(i.id for i in cls._filter_with_users(items, current_user.reload(), to_move=True))[:]
        myitems_ids = orm.select(i.id for i in items.filter(lambda i: i.user == current_user))[:] if current_user.can_access('FromWithMeMoveStock') else []    
        orphaned = cls._filter_orphaned(items) if current_user.can_access('FromOrphanedMoveStock') else []
        other_ids = instockitems_ids+withusersitems_ids+myitems_ids
        items = items.filter(lambda i: (i in orphaned or i.id in other_ids) and i.device != None and i.status not in [StockStatus.installed])
        
        return items


    @classmethod
    def _filter_with_user_clients(cls, items, user, managed_by=None, entity=None):
        clients = ClientGetterService.get_list(user, managed_by=managed_by, entity=entity, extra_permission="WithClientsViewStock")
        ids = orm.select(c.id for c in clients)[:]
        return items.filter(lambda s: s.client.id in ids)

    @classmethod
    def _filter_in_stock(cls, items, user, entity=None, managed_by=None, to_move=False):
        p = 'FromInStockMoveStock' if to_move else 'InStockViewStock'
        entities = user.get_entities_with_permission(p)
        if entity:
            entities = entities.filter(lambda e: e == entity)
        if managed_by:
            entities = entities.filter(lambda e: e in user.managed_operational_entities)
        return items.filter(lambda s: s.shop in entities)

    @classmethod
    def _filter_with_users(cls, items, user, entity=None, to_move=False):
        users = UserGetterService.get_list(user, entity=entity)
        p = 'FromUsersMoveStock' if to_move else 'WithUsersViewStock'
        users = users.filter(lambda u: u.shop in user.get_entities_with_permission(p))
        return items.filter(lambda i: i.user in users)

    @classmethod
    def _filter_orphaned(cls, items, for_sale=False):
        if for_sale:
            return items.filter(lambda i: i.status == StockStatus.orphaned)
        return items.filter(lambda i: i.status in [StockStatus.orphaned, StockStatus.lost])

    @classmethod
    def user_can_see(cls, stock_item, user):
        if stock_item.status in [StockStatus.orphaned, StockStatus.lost] and user.can_access('OrphanedViewStock'):
            return True
        if stock_item.user == user and user.can_access('WithMeViewStock'):
            return True
        if stock_item.shop:
            in_stock_entities = user.get_entities_with_permission('InStockViewStock')
            if in_stock_entities.filter(lambda e: e.id == stock_item.shop.id).count() > 0:
                return True
        if stock_item.user and stock_item.user.shop:
            users_entities = user.get_entities_with_permission('WithUsersViewStock')
            if users_entities.filter(lambda e: e.id == stock_item.user.shop.id).count() > 0:
                return True
        if stock_item.client:
            clients = ClientGetterService.get_list(user, extra_permission="WithClientsViewStock")
            if clients.filter(lambda e: e.id == stock_item.client.id).count() > 0:
                return True
        return False
   