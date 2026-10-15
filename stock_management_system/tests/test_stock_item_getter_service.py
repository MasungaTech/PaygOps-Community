from random import randint

from pony.orm import db_session, flush, select

from core_system.core_entities import db
from core_system.users.models.user_model import User
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from shared.helpers.client_creator import ClientCreator
from stock_management_system.services.stock_item_getter_service import StockItemGetterService
from stock_management_system.services.stock_movement_creation_service import (
    StockMovementCreationService,
)
from stock_management_system.stock_status import StockStatus


class TestStockItemGetterMovableItems:

    def _new_npg_device(self, serial_suffix=None):
        serial = serial_suffix or str(randint(10000000, 99999999))
        return DeviceCreateService.create(
            serial_number=serial,
            device_type='NPG',
            mode=1,
        )

    def _movable_ids(self, user):
        return select(i.id for i in StockItemGetterService.get_movable_items(user))[:]

    @db_session
    def test_installed_items_excluded_from_movable_items(self, api_client, good_api_key):
        user = User.get(username='super_admin@test.com')
        assert user

        installed_device = self._new_npg_device()
        orphaned_device = self._new_npg_device()
        in_stock_device = self._new_npg_device()
        with_user_device = self._new_npg_device()
        flush()

        client = ClientCreator.create(api_client, good_api_key)
        StockMovementCreationService.create(
            installed_device.stock_item,
            StockStatus.installed,
            destination_client=client,
            user=user,
            manual=False,
        )
        StockMovementCreationService.create(
            in_stock_device.stock_item,
            StockStatus.in_stock,
            destination_entity=db.Hub.select().first(),
            user=user,
            manual=False,
        )
        StockMovementCreationService.create(
            with_user_device.stock_item,
            StockStatus.with_user,
            destination_user=user,
            user=user,
            manual=False,
        )
        flush()

        assert installed_device.stock_item.status == StockStatus.installed
        assert orphaned_device.stock_item.status == StockStatus.orphaned
        assert in_stock_device.stock_item.status == StockStatus.in_stock
        assert with_user_device.stock_item.status == StockStatus.with_user

        movable_ids = self._movable_ids(user)

        assert installed_device.stock_item.id not in movable_ids
        assert orphaned_device.stock_item.id in movable_ids
        assert in_stock_device.stock_item.id in movable_ids
        assert with_user_device.stock_item.id in movable_ids

    @db_session
    def test_installed_items_excluded_for_restricted_move_permissions(
        self, api_client, good_api_key
    ):
        agent = User.get(username='agent@test.com')
        assert agent

        installed_device = self._new_npg_device()
        orphaned_device = self._new_npg_device()
        flush()

        client = ClientCreator.create(api_client, good_api_key)
        StockMovementCreationService.create(
            installed_device.stock_item,
            StockStatus.installed,
            destination_client=client,
            user=agent,
            manual=False,
        )
        flush()

        movable_ids = self._movable_ids(agent)

        assert installed_device.stock_item.id not in movable_ids
        if agent.can_access('FromOrphanedMoveStock'):
            assert orphaned_device.stock_item.id in movable_ids
