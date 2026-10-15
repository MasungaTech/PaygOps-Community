from datetime import datetime
from flask_login import current_user
from pony.orm import db_session, flush
import pytest
from shared.helpers.client_creator import ClientCreator
from shared.logger.loggers import Error
from stock_management_system.models import StockItem
from stock_management_system.stock_status import StockStatus
from stock_management_system.services.stock_movement_creation_service import (
    StockMovementCreationService)
from payg_loan_system.devices.services.create_device_service import DeviceCreateService



class TestStockMovementCreationService:

    @db_session
    def test_default_stock_movement_values(self):

        stock = StockItem.select().first()
        StockMovementCreationService.create(stock, StockStatus.lost, manual=False)

        flush()

        assert (stock.last_movement.date.replace().replace(second=0, microsecond=0) ==
                datetime.now().replace(second=0, microsecond=0))
        assert stock.last_movement.user == current_user
        assert stock.status == StockStatus.lost

    @db_session
    def test_multiple_stock_items_movements(self):

        items = StockItem.select().limit(2)
        stock1 = items[0]
        stock2 = items[1]
        StockMovementCreationService.create(
            [stock1, stock2], StockStatus.lost, manual=False, suppress_errors=True
        )

        flush()

        assert stock1.status == StockStatus.lost
        assert stock2.status == StockStatus.lost

    @db_session
    def test_multiple_stock_items_movements_manual(self):

        device1 = DeviceCreateService.create('1234%4321', 'NPG', 1)
        device2 = DeviceCreateService.create('1234%43212', 'NPG', 1)

        flush()
        StockMovementCreationService.create(
            [device1.stock_item, device2.stock_item], StockStatus.lost, suppress_errors=True
        )

        flush()

        assert device1.stock_item.status == StockStatus.lost
        assert device2.stock_item.status == StockStatus.lost

    @db_session
    def test_manual_restrictions_on_stock_movements(self, api_client, good_api_key):

        #add here tests of permissions
        stock = StockItem.select().first()
        StockMovementCreationService.create(stock, StockStatus.orphaned, manual=False)

        with pytest.raises(Error) as error:
            StockMovementCreationService.create(stock, StockStatus.installed)
        assert error.value.code == 'MANUAL_STOCK_TO_CLIENT'

        client = ClientCreator.create(api_client, good_api_key)

        StockMovementCreationService.create(
            stock, StockStatus.installed, destination_client=client, manual=False
        )
        flush()

        with pytest.raises(Error) as error:
            StockMovementCreationService.create(stock, StockStatus.lost)
        assert error.value.code == 'MANUAL_STOCK_INSTALLED'
