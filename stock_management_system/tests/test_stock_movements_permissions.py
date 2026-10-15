from random import randint
from stock_management_system.services.stock_item_getter_service import StockItemGetterService
from pony import orm
from core_system.users.models.user_model import User
from core_system.core_entities import db
from stock_management_system.services.stock_movement_creation_service import StockMovementCreationService
from tests.factories import user_mock
from tests.base_test import BaseViewTest
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from stock_management_system.services.permission_helpers import StockMovementPermissionHelper

class TestStockMovementsPermissions():

    @orm.db_session
    def _get_user(self, role='SuperAdmin'):
        this_username = role+'@stockpermissions.com'
        this_user = User.get(username=this_username)
        if not this_user:
            this_user = user_mock.create_user('Test',
                                              role+'Stock',
                                              this_username,
                                              '+23411'+str(randint(10000000, 99999999)),
                                              role)
            this_user.roles_in_entities.create(sync_entity=True)
        return this_user

    @orm.db_session
    def _new_npg_device(self):
        number = randint(1, 99999999)
        device = DeviceCreateService.create(
            serial_number=str(number),
            device_type='NPG',
            mode=1
        )
        return device

    @orm.db_session
    def test_stock_user_view_and_move(self):

        admin = self._get_user('Admin')
        accountant = self._get_user('Accountant')
        super_manager = self._get_user('SuperManager')
        manager = self._get_user('Manager')
        agent = self._get_user('Agent')
        view_only = self._get_user('ViewOnly')

        device = self._new_npg_device()

        assert StockItemGetterService.user_can_see(device.stock_item, admin)
        assert StockItemGetterService.user_can_see(device.stock_item, accountant)
        assert StockItemGetterService.user_can_see(device.stock_item, super_manager)
        assert StockItemGetterService.user_can_see(device.stock_item, manager)
        assert StockItemGetterService.user_can_see(device.stock_item, agent)
        assert StockItemGetterService.user_can_see(device.stock_item, view_only)

        d = {
            'status': 'lost',
            'user': None,
            'shop': None
        }
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, admin)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, accountant)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, super_manager)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, manager)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, agent)
        assert not StockMovementPermissionHelper.user_can_move(device.stock_item, d, view_only)

        d = {
            'status': 'in_stock',
            'user': None,
            'shop': db.Hub.get(name="Shop1")
        }
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, admin)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, accountant)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, super_manager)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, manager)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, agent)
        assert not StockMovementPermissionHelper.user_can_move(device.stock_item, d, view_only)
        
        d = {
            'status': 'in_stock',
            'user': None,
            'shop': db.Hub.get(name="Shop3")
        }
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, admin)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, accountant)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, super_manager)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, manager)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, agent)
        assert not StockMovementPermissionHelper.user_can_move(device.stock_item, d, view_only)
        
        d = {
            'status': 'in_stock',
            'user': admin,
            'shop': None
        }
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, admin)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, accountant)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, super_manager)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, manager)
        assert StockMovementPermissionHelper.user_can_move(device.stock_item, d, agent)
        assert not StockMovementPermissionHelper.user_can_move(device.stock_item, d, view_only)
        
        entity = db.Hub.select().first()
        StockMovementCreationService.create(device.stock_item, 'in_stock', destination_entity=entity)
        orm.flush()
        
        assert StockItemGetterService.user_can_see(device.stock_item, admin)
        assert StockItemGetterService.user_can_see(device.stock_item, accountant)
        assert StockItemGetterService.user_can_see(device.stock_item, super_manager)
        assert StockItemGetterService.user_can_see(device.stock_item, manager)
        assert StockItemGetterService.user_can_see(device.stock_item, agent)
        assert StockItemGetterService.user_can_see(device.stock_item, view_only)


class TestStockMovementsStockListView(BaseViewTest):
    url = 'stock.stock_list'
    template = 'stock_list.html'

class TestStockMovementsMovementsView(BaseViewTest):
    url = 'stock.stock_movements'
    template = 'stock_movements.html'

class TestStockMovementsAddMovementsView(BaseViewTest):
    url = 'stock.add_movements'
    template = 'add_movements.html'
