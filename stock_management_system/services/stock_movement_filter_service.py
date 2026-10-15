from flask_login import current_user
from datetime import timedelta
from stock_management_system.quantity_stock_models import QuantityStockMovement
from stock_management_system.stock_status import StockStatus, StockMovementStatus
from shared.helpers import date_helper
from shared.helpers.clock import Clock
from pony.orm import coalesce, select

class StockMovementFilterService:

    @classmethod
    def filter(cls, stock_movements, begin_date=None, end_date=None, search='', origin_status=None,
                      origin_user=None, origin_client=None, origin_shop=None, destination_status=None, accepted_status=None,
                      destination_user=None, destination_client=None, destination_shop=None, product_type=None, product_subtype=None,
                      my_pending_stock_only=None):
        
        if search != '':
            stock_movements = stock_movements.filter(
                lambda move: search.lower() in (
                    move.stock_item.device.composed_serial
                ).lower()
            )

        if begin_date:
            date = date_helper.formatDateStringToDate(begin_date)
            date = Clock.localize_to_utc(date)
            stock_movements = stock_movements.filter(
                lambda move: move.date >= date)

        if end_date:
            date = date_helper.formatDateStringToDate(end_date)+timedelta(days=1)
            date = Clock.localize_to_utc(date)
            stock_movements = stock_movements.filter(
                lambda move: move.date < date)

        if origin_status:
            if origin_user and origin_status == StockStatus.with_user:
                stock_movements = stock_movements.filter(
                    lambda move: origin_user.lower() in (
                        move.origin_user.person.name
                        + ' ' + move.origin_user.person.surname
                        + ' ' + str(move.origin_user.id)
                    ).lower()
                )
            elif origin_client and origin_status == StockStatus.installed:
                stock_movements = stock_movements.filter(
                    lambda move: origin_client.lower() in (
                        move.origin_client.person.name
                        + ' ' + move.origin_client.person.surname
                        + ' ' + str(move.origin_client.id)
                    ).lower()
                )
            elif origin_shop and origin_status == StockStatus.in_stock:
                stock_movements = stock_movements.filter(
                    lambda move: move.origin_shop.id == origin_shop)
            else:
                stock_movements = stock_movements.filter(
                    lambda move: move.origin_status == origin_status)

        if destination_status and destination_status != 'any':
            if destination_user and destination_status == StockStatus.with_user:
                stock_movements = stock_movements.filter(
                    lambda move: destination_user.lower() in (
                        move.destination_user.person.name
                        + ' ' + move.destination_user.person.surname
                        + ' ' + str(move.destination_user.id)
                    ).lower()
                )
            elif destination_client and destination_status == StockStatus.installed:
                stock_movements = stock_movements.filter(
                    lambda move: destination_client.lower() in (
                        move.destination_client.person.name
                        + ' ' + move.destination_client.person.surname
                        + ' ' + str(move.destination_client.id)
                    ).lower()
                )
            elif destination_shop and destination_status == StockStatus.in_stock:
                stock_movements = stock_movements.filter(
                    lambda move: move.destination_entity.id == destination_shop)
            else:
                stock_movements = stock_movements.filter(
                    lambda move: move.destination_status == destination_status)
        
        if accepted_status and accepted_status != 'any':
            stock_movements = stock_movements.filter(
                    lambda move: move.approval_status == accepted_status 
            )

        if product_type:
            stock_movements = stock_movements.filter(
                lambda move: move.stock_item.device.type == product_type 
            )

        if product_subtype:
            stock_movements = stock_movements.filter(
                lambda move: move.stock_item.device.product_sub_type.id == product_subtype
            )
 
        if my_pending_stock_only in ["true", True]:
            stock_movements = stock_movements.filter(
                    lambda move: move.approval_status == StockMovementStatus.pending
                                and  move.destination_user.id == current_user.id
            )

        return stock_movements
    
    @classmethod
    def filter_quantity(
        cls, stock_movements, begin_date=None, end_date=None, search='', origin_status=None,
        origin_user=None, origin_client=None, origin_shop=None, destination_status=None, accepted_status=None,
        destination_user=None, destination_client=None, destination_shop=None, product_type=None, product_subtype=None,
        my_pending_stock_only=False):

        if search != '':
            stock_movements = stock_movements.filter(
                lambda move: search.lower() in coalesce(
                    move.origin.product_sub_type.name,
                    move.destination.product_sub_type.name,
                ).lower()
            )

        if begin_date:
            date = date_helper.formatDateStringToDate(begin_date)
            date = Clock.localize_to_utc(date)
            stock_movements = stock_movements.filter(
                lambda move: move.date >= date
            )

        if end_date:
            date = date_helper.formatDateStringToDate(end_date)+timedelta(days=1)
            date = Clock.localize_to_utc(date)
            stock_movements = stock_movements.filter(
                lambda move: move.date < date
            )

        if origin_status:
            if origin_user and origin_status == StockStatus.with_user:
                stock_movements = stock_movements.filter(
                    lambda move: origin_user.lower() in (
                        move.origin.user.person.name
                        + ' ' + move.origin.user.person.surname
                        + ' ' + str(move.origin.user.id)
                    ).lower()
                )
            elif origin_client and origin_status == StockStatus.installed:
                # todo
                pass
            elif origin_shop and origin_status == StockStatus.in_stock:
                stock_movements = stock_movements.filter(
                    lambda move: move.origin.operational_entity.id == origin_shop
                )
            else:
                stock_movements = stock_movements.filter(
                    lambda move: move.origin.status == origin_status
                )
                
        if destination_status and destination_status != 'any':
            if destination_user and destination_status == StockStatus.with_user:
                stock_movements = stock_movements.filter(
                    lambda move: destination_user.lower() in (
                        move.destination.user.person.name
                        + ' ' + move.destination.user.person.surname
                        + ' ' + str(move.destination.user.id)
                    ).lower()
                )
            elif destination_client and destination_status == StockStatus.installed:
                #todo
                pass
            elif destination_shop and destination_status == StockStatus.in_stock:
                stock_movements = stock_movements.filter(
                    lambda move: move.destination.operational_entity.id == destination_shop
                )
            else:
                stock_movements = stock_movements.filter(
                    lambda move: move.destination.status == destination_status
                )

        if accepted_status and accepted_status != 'any':
            stock_movements = stock_movements.filter(
                    lambda move: move.approval_status == accepted_status 
            )

        # Product type filter
        if product_type:
            stock_movements = cls.combine_origin_destination_filters(
                stock_movements,
                match_both=lambda m: (
                    m.origin.product_sub_type.device_type == product_type or
                    m.destination.product_sub_type.device_type == product_type
                ),
                match_origin_only=lambda m: m.origin.product_sub_type.device_type == product_type,
                match_destination_only=lambda m: m.destination.product_sub_type.device_type == product_type,
            )

        # Product subtype filter
        if product_subtype:
            stock_movements = cls.combine_origin_destination_filters(
                stock_movements,
                match_both=lambda m: (
                    m.origin.product_sub_type.id == product_subtype or
                    m.destination.product_sub_type.id == product_subtype
                ),
                match_origin_only=lambda m: m.origin.product_sub_type.id == product_subtype,
                match_destination_only=lambda m: m.destination.product_sub_type.id == product_subtype,
            )

        if my_pending_stock_only in ["true", True]:
            stock_movements = stock_movements.filter(
                    lambda move: move.approval_status == StockMovementStatus.pending
                                and  move.destination.user.id == current_user.id
            )

        return stock_movements
    


    @staticmethod
    def combine_origin_destination_filters(base_query, match_both=None, match_origin_only=None, match_destination_only=None):
        queries = []

        if match_both:
            queries.append(select(m.id for m in QuantityStockMovement
                                if m in base_query
                                and m.origin is not None and m.destination is not None
                                and match_both(m)))

        if match_origin_only:
            queries.append(select(m.id for m in QuantityStockMovement
                                if m in base_query
                                and m.origin is not None and m.destination is None
                                and match_origin_only(m)))

        if match_destination_only:
            queries.append(select(m.id for m in QuantityStockMovement
                                if m in base_query
                                and m.destination is not None and m.origin is None
                                and match_destination_only(m)))

        if not queries:
            return base_query

        all_result_ids = set()
        for q in queries:
            all_result_ids |= set(q)

        return select(m for m in QuantityStockMovement if m.id in all_result_ids)

    @staticmethod
    def get_pending_serialized_stock_movement_count(serialized_stock_movements):
        return serialized_stock_movements.filter(
                lambda move: move.approval_status == StockMovementStatus.pending
                        and  move.destination_user.id == current_user.id
            ).count()
    
    @staticmethod
    def get_pending_quantity_stock_movement_count(quantity_stock_movements):
        return quantity_stock_movements.filter(
                lambda move: move.approval_status == StockMovementStatus.pending
                    and  move.destination.user.id == current_user.id
            ).count()
