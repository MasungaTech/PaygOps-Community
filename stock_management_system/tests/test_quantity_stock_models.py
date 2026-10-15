from datetime import datetime

from pony.orm import db_session, flush, rollback

from config import API_PREFIX
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from stock_management_system.quantity_stock_models import (
    QuantityStockLocation,
    QuantityStockMovement,
)
from stock_management_system.stock_status import StockMovementStatus, StockStatus


class TestQuantityStockMovementSerialization:

    def _create_movement_from_orphaned_origin(self, user):
        product = ProductSubType(
            name='Qty movement origin no entity',
            sku='qty-origin-no-entity',
            device_type='NPG',
            is_serialized=False,
        )
        origin = QuantityStockLocation(
            product_sub_type=product,
            status=StockStatus.orphaned,
            total_quantity=0,
        )
        destination = QuantityStockLocation(
            product_sub_type=product,
            status=StockStatus.lost,
            total_quantity=0,
        )
        QuantityStockMovement(
            date=datetime.now(),
            user=user,
            quantity=2,
            destination=origin,
            approval_status=StockMovementStatus.accepted,
        )
        # Flush the inbound movement first so origin quantity stays coherent
        # when the outbound movement is inserted.
        flush()
        return QuantityStockMovement(
            date=datetime.now(),
            user=user,
            note='from orphaned origin',
            quantity=1,
            origin=origin,
            destination=destination,
            approval_status=StockMovementStatus.accepted,
        )

    @db_session
    def test_serialize_when_origin_has_no_operational_entity(self, super_admin_user):
        movement = self._create_movement_from_orphaned_origin(super_admin_user())
        try:
            assert movement.origin.operational_entity is None
            serialized = movement.get_serialized_object()
            assert serialized['origin_entity_id'] is None
            assert serialized['destination_entity_id'] is None
        finally:
            rollback()

    @db_session
    def test_list_include_objects_when_origin_has_no_entity(
        self, api_client, admin_api_key, super_admin_user
    ):
        self._create_movement_from_orphaned_origin(super_admin_user())
        flush()
        try:
            response = api_client.get(
                API_PREFIX + '/quantity_stock_movements',
                query_string={'include_objects': 'True'},
                headers={'Authorization': 'Bearer ' + admin_api_key},
            )
            assert response.status_code == 200, response.json
            matching = [
                item for item in response.json
                if item.get('note') == 'from orphaned origin'
            ]
            assert matching
            assert matching[0]['origin_entity_id'] is None
        finally:
            rollback()
