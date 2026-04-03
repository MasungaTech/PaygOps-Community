from core_system.users.models.user_model import User
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from mock import patch
from datetime import datetime
from core_system.client.models import Client
from tests.factories.factories import AbstractUserFactory
from payg_loan_system.devices.factories import DeviceAbstractFactory
from payg_loan_system.actions.deregister import handle_deregistration_request
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.contracts.services.tests.factories import ContractFactory
import pytest
from pony.orm import db_session

class TestDeRegister:

    @db_session
    def test_user_without_auth(self, *args):
        user = User.get(username="view_only@test.com")
        this_device = DeviceAbstractFactory.create()

        resp = handle_deregistration_request(user, this_device)

        assert resp[0]['status'] == 'STOCK_ITEM_NOT_VISIBLE'

    @db_session
    def test_old_device_not_registered(self, super_admin_user, *args):
        user = super_admin_user()
        this_device = DeviceCreateService.create('TESTDEVICEPERM', 'NPG', 1) # DeviceAbstractFactory.create_no_client()


        resp = handle_deregistration_request(user, this_device)

        assert resp == [{'success': False, 'status': 'DEVICE_NOT_REGISTERED'}]
        this_device.delete()

    @pytest.mark.skip(reason='Impossible to mock the stuff properly')
    @patch('payg_loan_system.actions.deregister.save_mentor_request')
    @patch.object(DeviceAPIService, 'sync_device_settings', return_value='PANCAKES')
    @patch('payg_loan_system.actions.swap_device.save_mentor_request')
    def test_deregister_success(self,super_admin_user, *args):
        user = super_admin_user()
        this_device = DeviceAbstractFactory.create()
        this_device.contract = ContractFactory.stub()

        device_client = this_device.contract.client

        resp = handle_deregistration_request(user, this_device)

        assert resp == [{'success': True,
                        'status': 'CLIENT_DEREGISTRATION_SUCCESS',
                        'client_id': device_client.id,
                        'name': device_client.person.name,
                        'surname': device_client.person.surname}]
        assert device_client.termination_date.replace(microsecond=0, second=0) == datetime.now().replace(microsecond=0, second=0)
