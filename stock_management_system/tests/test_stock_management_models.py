from datetime import datetime, timedelta
from shared.helpers.client_creator import ClientCreator
import pytest
from pony.orm import db_session, flush, commit
from stock_management_system.models import StockItem, StockMovement
from stock_management_system.stock_status import StockStatus
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from payg_loan_system.devices.model.device import Device
from core_system.core_entities import db
from core_system.client.models import Client
from core_system.role.models import Role
from core_system.users.services.edit_user_service import EditUserService
from core_system.users.models.user_model import User
from config import ORGANIZATION_LIST


class TestStockManagementSystemService:

    def test_stock_statuses_definition(self):

        human_names = {}
        human_names.update(StockStatus._human_codes)

        for key in StockStatus.keys():
            assert getattr(StockStatus, key) in human_names
            del human_names[key]
        assert not human_names

    def test_data_coherence_checking(self, api_client, good_api_key):

        device = DeviceCreateService.create(serial_number='1',
                                            mode=1,
                                            device_type='NPG')
        device_id = device.id

        with db_session:
            shop = db.Hub(name='TEST SHOP', user_in_charge=User.select().first(), parent=db.Zone.select().first())
        shop_id = shop.id

        with db_session:
            user = User.select().first()
            if not user:
                user = EditUserService.add_user(
                    'test', 'user', 'test@user.com', '12341234',
                    Role(name='TEST_ROLE', type=1), db.Hub[shop_id],
                    organization=ORGANIZATION_LIST[0]
                )
        user_id = user.id

        with db_session:
            client = ClientCreator.create(api_client, good_api_key)
        client_id = client.id

        with pytest.raises(Exception, match='Check for attribute StockMovement.destination_status failed. Value: \'TEST_WRONG_STATUS\''):
            with db_session:
                StockMovement(stock_item=Device[device_id].stock_item,
                              date=datetime.now(),
                              destination_status='TEST_WRONG_STATUS')

        coherent_cases = {
            StockStatus.orphaned: {'u': None, 'c': None, 's': None},
            StockStatus.lost: {'u': None, 'c': None, 's': None},
            StockStatus.in_stock: {'u': None, 'c': None, 's': shop_id},
            StockStatus.installed: {'u': None, 'c': client_id, 's': None},
            StockStatus.with_user: {'u': user_id, 'c': None, 's': None},
        }

        for status in StockStatus.keys():
            for u in [user_id, None]:
                for c in [client_id, None]:
                    for s in [shop_id, None]:
                        if (coherent_cases[status]['u'] != u or
                                coherent_cases[status]['c'] != c or
                                coherent_cases[status]['s'] != s):

                            with pytest.raises(Exception, match='STATUS_LOCATION_INCOHERENCE'):
                                with db_session:
                                    user = User.get(id=u) if u else None
                                    client = Client.get(id=c) if c else None
                                    shop = db.Hub.get(id=s) if s else None
                                    print(status)
                                    StockMovement(stock_item=Device[device_id].stock_item,
                                                  date=datetime.now(),
                                                  destination_status=status,
                                                  destination_user=user,
                                                  destination_client=client,
                                                  destination_entity=shop)

    @db_session
    def test_stock_movements_relations(self):

        device = DeviceCreateService.create(serial_number='2',
                                            mode=1,
                                            device_type='NPG')
        flush()

        assert StockMovement.get(stock_item=device.stock_item) == device.stock_item.last_movement
        assert device.stock_item.status == StockStatus.orphaned

        first_movement = device.stock_item.last_movement
        second_movement = StockMovement(stock_item=device.stock_item,
                                        date=datetime.now(),
                                        destination_status=StockStatus.lost)
        
        flush()
        
        assert device.stock_item.last_movement == second_movement
        assert second_movement.previous == first_movement
        
        with pytest.raises(Exception, match='restricted property'):
            StockItem(last_movement=first_movement)
            commit()

    def test_movements_date_coherence(self):
        
        device = DeviceCreateService.create(serial_number='3',
                                            mode=1,
                                            device_type='NPG')
        device_id = device.id
        
        with pytest.raises(Exception, match='date has to be later'):
            with db_session:
                StockMovement(stock_item=Device[device_id].stock_item,
                              date=datetime.now()-timedelta(hours=3),
                              destination_status=StockStatus.lost)
                
        with pytest.raises(Exception, match='cannot be earlier in time'):
            with db_session:
                move = StockMovement(stock_item=Device[device_id].stock_item,
                                     date=datetime.now()+timedelta(seconds=5),
                                     destination_status=StockStatus.lost)
                flush()
                move.date = datetime.now()-timedelta(hours=3)
