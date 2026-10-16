from shared.logger.loggers import Error
from stock_management_system.models import StockMovement
from stock_management_system.quantity_stock_models import QuantityStockMovement
from stock_management_system.services.permission_helpers import StockMovementPermissionHelper
from stock_management_system.stock_status import StockMovementStatus, StockStatus


class AcceptRejectStockMovementService:

    @classmethod
    def accept_movement(cls, movement, user, note):
        if not movement.approval_status == StockMovementStatus.pending:
            raise Error('This movement is not pending and cannot be accepted')
        if not cls.can_move(user, movement):
            raise Error('You do not have the permissions to accept this stock movement')
        if isinstance(movement, StockMovement):
            if movement.destination_user and movement.destination_user != user:
                raise Error('You cannot approve a stock movement that is not assigned to you')
        elif isinstance(movement, QuantityStockMovement):
            if movement.destination.user and movement.destination.user != user:
                raise Error('You cannot approve a stock movement that is not assigned to you')
        movement.approval_status = StockMovementStatus.accepted
        if isinstance(movement, QuantityStockMovement):
            movement.destination.check_coherence()
            movement.origin.check_coherence()
            movement.destination.total_quantity += movement.quantity
            movement.origin.total_quantity -= movement.quantity

        if note:
            movement.receiving_note = note
        return movement

    @classmethod
    def reject_movement(cls, movement, user, note=''):
        if not movement.approval_status == StockMovementStatus.pending:
            raise Error('This movement is not pending and cannot be rejected')
        if not cls.can_move(user, movement):
            raise Error('You do not have the permissions to reject this stock movement')
        if movement.destination_user and movement.destination_user != user:
            raise Error('You cannot reject a stock movement that is not assigned to you')
        movement.approval_status = StockMovementStatus.rejected
        if isinstance(movement, StockMovement):
            movement.stock_item.last_movement = movement.previous
        if note:
            movement.receiving_note = note
        return movement

    @classmethod
    def can_move(cls, user, movement):
        if isinstance(movement, StockMovement):
            stock_item = movement.stock_item
            if not stock_item:
                raise Error('Stock Item not found')
            return StockMovementPermissionHelper.user_can_move(stock_item, {
                'status': movement.destination_status,
                'user': movement.destination_user,
                'shop': movement.destination_entity
            }, user)

        if isinstance(movement, QuantityStockMovement):
            destination = movement.destination

            if destination.user == user:
                user.check_access('ToWithMeMoveStock')
            elif destination.user:
                user.check_access('ToUsersMoveStock', destination.user.shop)
            if destination.status == StockStatus.in_stock:
                user.check_access('ToInStockMoveStock', destination.operational_entity)
            
            return True
        raise Error('Unsupported movement type')
