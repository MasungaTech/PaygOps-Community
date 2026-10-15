import json
from random import randint

from flask import url_for
from pony.orm import db_session, flush

from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from shared.helpers.client_creator import ClientCreator
from stock_management_system.services.stock_movement_creation_service import (
    StockMovementCreationService,
)
from stock_management_system.stock_status import StockStatus
from tests.base_test import BaseViewTest


class TestStockItemListView(BaseViewTest):
    url = 'stock.stock_list'
    template = 'stock_list.html'


class TestStockMovementListView(BaseViewTest):
    url = 'stock.stock_movements'
    template = 'stock_movements.html'


class TestAddStockMovementView(BaseViewTest):
    url = 'stock.add_movements'
    template = 'add_movements.html'

    @db_session
    def test_device_code_adder_excludes_installed_items(
        self, super_admin_app, api_client, good_api_key, context
    ):
        serial = str(randint(10000000, 99999999))
        installed_device = DeviceCreateService.create(
            serial_number=serial,
            device_type='NPG',
            mode=1,
        )
        orphaned_serial = str(randint(10000000, 99999999))
        orphaned_device = DeviceCreateService.create(
            serial_number=orphaned_serial,
            device_type='NPG',
            mode=1,
        )
        flush()

        client = ClientCreator.create(api_client, good_api_key)
        StockMovementCreationService.create(
            installed_device.stock_item,
            StockStatus.installed,
            destination_client=client,
            manual=False,
        )
        flush()

        installed_serial = installed_device.composed_serial
        orphaned_composed = orphaned_device.composed_serial

        with context:
            installed_response = super_admin_app.get(
                url_for(self.url),
                query_string={'source': 'device_code_adder', 'q': installed_serial},
            )
            orphaned_response = super_admin_app.get(
                url_for(self.url),
                query_string={'source': 'device_code_adder', 'q': orphaned_composed},
            )

        assert installed_response.status_code == 200
        installed_results = json.loads(installed_response.data)
        assert installed_serial not in [
            r['text'] for r in installed_results.get('results', [])
        ]

        assert orphaned_response.status_code == 200
        orphaned_results = json.loads(orphaned_response.data)
        assert orphaned_composed in [
            r['text'] for r in orphaned_results.get('results', [])
        ]
