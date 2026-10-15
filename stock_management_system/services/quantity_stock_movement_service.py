from datetime import datetime

from pony.orm import flush

from core_system.client.services.client_getter_service import ClientGetterService
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from core_system.users.services.user_getter_service import UserGetterService
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService
from shared.services.base_service import BaseService
from shared.services.settings_service import SettingsService
from stock_management_system.quantity_stock_models import (
    QuantityStockLocation, QuantityStockMovement)
from stock_management_system.services.product_sub_type_service import \
    ProductSubTypeService
from stock_management_system.stock_status import (StockMovementStatus,
                                                  StockStatus)
from stock_management_system.services.stock_movement_accept_reject_service import AcceptRejectStockMovementService


class QuantityStockMovementService(BaseGetterService, BaseService):

    @classmethod
    def get_filtered_objects(cls, current_user=None, created_by=None, assigned_to=None, **kwargs):
        if created_by:
            return QuantityStockMovement.select(lambda m: m.user == created_by)
        if assigned_to:
            return QuantityStockMovement.select(lambda m: m.destination.user == assigned_to)
        return QuantityStockMovement.select()

    @staticmethod
    def _get_stock_item(acting_user, product_sub_type, data, place='origin'):

        if not data:
            return
        status = StockStatus.ovalidate(data.get('status'))
        user = UserGetterService.extract_from_user_and_id(acting_user, data, 'user_id')
        entity = OperationalEntitiesGetterService.extract_from_user_and_id(
            acting_user, data, "entity_id"
        )
        client = ClientGetterService.extract_from_user_and_id(acting_user, data, 'client_id')

        if user and entity:
            raise Error(
                'Not possible to provide {place} user and entity at the same time', place=place
            )
        if status in [StockStatus.lost, StockStatus.orphaned] and (user or entity):
            raise Error(
                'You cannot provide {place} user or entity if {place} status is orphaned or lost',
                place=place
            )
        if status == StockStatus.with_user and not user:
            raise Error('Missing {place} user', place=place)
        if status == StockStatus.in_stock and not entity:
            raise Error('Missing {place} entity', place=place)

        location = QuantityStockLocation.get(
            product_sub_type=product_sub_type,
            status=status,
            user=user,
            operational_entity=entity,
            client=client
        ) or QuantityStockLocation(
            product_sub_type=product_sub_type,
            status=status,
            user=user,
            client=client,
            operational_entity=entity,
            total_quantity=0
        )

        return location

    @classmethod
    def _add_from_data_and_user(cls, data, user, **kwargs):
        product_sub_type = ProductSubTypeService.extract_from_user_and_id(
            user, data, "product_sub_type_id", empty_allowed=False
        )

        if product_sub_type.is_serialized:
            raise Error('You cannot use quantity based inventory for serialized Products')

        # Get origin data - either from 'origin' object or from individual fields
        origin_data = data.get('origin')
        if not origin_data:
            # Construct origin_data from individual fields if they exist
            if any(key.startswith('origin_') for key in data.keys()):
                origin_data = {}
                if 'origin_status' in data:
                    origin_data['status'] = data['origin_status']
                if 'origin_user_id' in data:
                    origin_data['user_id'] = data['origin_user_id']
                if 'origin_entity_id' in data:
                    origin_data['entity_id'] = data['origin_entity_id']
                if 'origin_client_id' in data:
                    origin_data['client_id'] = data['origin_client_id']
        
        print('origin_data', origin_data)
        origin = cls._get_stock_item(user, product_sub_type, origin_data)

        # Get destination data - either from 'destination' object or from individual fields
        destination_data = data.get('destination')
        if not destination_data:
            # Construct destination_data from individual fields if they exist
            if any(key.startswith('destination_') for key in data.keys()):
                destination_data = {}
                if 'destination_status' in data:
                    destination_data['status'] = data['destination_status']
                if 'destination_user_id' in data:
                    destination_data['user_id'] = data['destination_user_id']
                if 'destination_entity_id' in data:
                    destination_data['entity_id'] = data['destination_entity_id']
                if 'destination_client_id' in data:
                    destination_data['client_id'] = data['destination_client_id']
        
        print('destination_data', destination_data)
        destination = cls._get_stock_item(user, product_sub_type, destination_data, 'destination')

        if not origin and not destination:
            raise Error('Either a valid origin or destination must be set')

        if origin == destination:
            raise Error('Origin and destination must be different')

        quantity = data["quantity"]
        if quantity < 0:
            quantity = -quantity
            origin, destination = destination, origin

        now = datetime.now()

        if not origin:
            if not destination.operational_entity:
                raise Error('Quantity Stock Items need to be added to an entity')
            user.check_access('AddMoveStock', destination.operational_entity)
        else:
            if origin.status == StockStatus.orphaned:
                user.check_access('FromOrphanedMoveStock')
            if origin.status == StockStatus.lost:
                user.check_access('FromLostMoveStock')
            if origin.user == user:
                user.check_access('FromWithMeMoveStock')
            elif origin.user:
                user.check_access('FromUsersMoveStock', origin.user.shop)
            if origin.status == StockStatus.in_stock:
                user.check_access('FromInStockMoveStock', origin.operational_entity)

        if not destination:
            if origin.status == StockStatus.installed:
                raise Error('Quantity Stock Items cannot be deleted when installed')
            user.check_access('DeleteMoveStock')
        else:
            if destination.status == StockStatus.orphaned:
                user.check_access('ToOrphanedMoveStock')
            if destination.status == StockStatus.lost:
                user.check_access('ToLostMoveStock')
            if destination.user == user:
                user.check_access('ToWithMeMoveStock')
            elif destination.user:
                user.check_access('ToUsersMoveStock', destination.user.shop)
            if destination.status == StockStatus.in_stock:
                user.check_access('ToInStockMoveStock', destination.operational_entity)
                # The or is only used when in the testing pipeline
                # to have a default since the setter is complex
                levels_enabled = SettingsService.get_setting(
                    'OperationalEntitiesInventory'
                ) or [True, True, True, False, False]
                level = destination.operational_entity.level
                if not levels_enabled[level]:
                    raise Error(f'Level {level} is not enabled for inventory management')

        approval_status = StockMovementStatus.accepted
        acknowledge_transfer = SettingsService.get_setting('AllowUsersToReceiveStock')
        if acknowledge_transfer and destination and destination.user and destination.user != user:
            approval_status = StockMovementStatus.pending

        if origin and quantity > origin.available_total_quantity:
            if origin.status != StockStatus.lost:
                raise Error(f'Not possible to move {quantity} items. There are only {origin.total_quantity} in that location.')

            QuantityStockMovement(
                date=now,
                user=user,
                note="Automatically created by adjustment",
                quantity=quantity-origin.total_quantity,
                destination=origin,
            )
            flush()

        movement = QuantityStockMovement(
            date=now,
            user=user,
            note=data.get("note", ""),
            quantity=quantity,
            origin=origin,
            destination=destination,
            approval_status=approval_status,
        )
        return movement

    @classmethod
    def _edit_from_data_and_user(cls, obj, data, user, **kwargs):
        if 'approval_status' in data:
            if data.get('approval_status') == StockMovementStatus.accepted:
                AcceptRejectStockMovementService.accept_movement(obj, user, data.get('note', ''))
            if data.get('approval_status') == StockMovementStatus.rejected:
                AcceptRejectStockMovementService.reject_movement(obj, user, data.get('note', ''))
