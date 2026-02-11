from stock_management_system.stock_status import StockStatus


class StockMovementPermissionHelper:

    @classmethod
    def user_can_move(cls, stock_item, destination, user):
        if cls._user_can_move_from(stock_item, user) and cls._user_can_move_to(destination, user):
            return True
        return False

    @classmethod
    def _user_can_move_from(cls, stock_item, user):

        if (stock_item.status == StockStatus.orphaned and
                user.can_access('FromOrphanedMoveStock')):
            return True
        if (stock_item.status == StockStatus.lost and
                user.can_access('FromLostMoveStock')):
            return True
        if stock_item.shop and user.can_access('FromInStockMoveStock', entity=stock_item.shop):
            return True
        if (stock_item.user and user.can_access('FromUsersMoveStock', entity=stock_item.user.shop)):
            return True
        if stock_item.user == user and user.can_access('FromWithMeMoveStock'):
            return True

        return False

    @classmethod
    def _user_can_move_to(cls, destination, user):

        if (destination['status'] == StockStatus.orphaned and
                user.can_access('ToOrphanedMoveStock')):
            return True
        if (destination['status'] == StockStatus.lost and
                user.can_access('ToLostMoveStock')):
            return True
        if destination['shop'] and user.can_access('ToInStockMoveStock', entity=destination['shop']):
            return True
        if (destination['user'] and user.can_access('ToUsersMoveStock', entity=destination['user'].shop)):
            return True
        if destination['user'] == user and user.can_access('ToWithMeMoveStock'):
            return True

        return False