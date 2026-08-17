from datetime import datetime, timedelta
from mock import patch
from pony.orm import db_session
from payg_loan_system.devices.factories import DeviceFactory
from payg_loan_system.devices.model.device import Device
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.actions.activation import handle_activation_request
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from core_system.client.models import Client
from shared.helpers.client_creator import ClientCreator
from tests.factories.factories import AbstractPaymentFactory

patcher_3 = patch.object(Client, 'get_payment_accounts')
patcher_3.start()


class TestHandleActivation:
    @db_session
    def test_no_activation_time_on_device(self, api_client, good_api_key):
        client = ClientCreator.create(api_client, good_api_key)
        with patch.object(Device, 'get_remaining_activation_time_in_hours', return_value=0), \
                patch.object(Payment, 'get', return_value=AbstractPaymentFactory.create()), \
                patch.object(Device, 'get', return_value=DeviceFactory.stub(client=None)), \
                patch.object(
                    DeviceGetterService, 'get_device_from_client_and_activation_code_optional',
                    return_value=DeviceFactory.stub()):
            res = handle_activation_request(client, 'foobar')

        assert len(res) == 1
        assert 'NO_ACTIVATION_TIME_ON_DEVICE' in str(res)

    @db_session
    def test_activation_time_on_device(self, api_client, good_api_key):
        client = ClientCreator.create(api_client, good_api_key)
        with patch.object(Payment, 'get', return_value=AbstractPaymentFactory.create()), \
                patch.object(Device, 'get', return_value=DeviceFactory.stub(client=None)), \
                patch.object(
                    DeviceGetterService, 'get_device_from_client_and_activation_code_optional',
                    return_value=DeviceFactory.stub(ActiveUntil=datetime.now()+timedelta(days=1))), \
                patch.object(DeviceAPIService, 'sync_device_activation', return_value='PATCH_CODE'):
            res = handle_activation_request(client, 'foobar')

        assert len(res) == 1
        assert 'ACTIVATION_REQUEST_SUCCESS' in str(res)

    @db_session
    def test_device_mode_unsupported(self, api_client, good_api_key):
        client = ClientCreator.create(api_client, good_api_key)
        with patch.object(Device, 'get', return_value=DeviceFactory.stub(Mode=2, client=None)), \
                patch.object(
                    DeviceGetterService, 'get_device_from_client_and_activation_code_optional',
                    return_value=DeviceFactory.stub(Mode=5)), \
                patch.object(DeviceAPIService, 'sync_device_activation', return_value='PATCH_CODE'):
            res = handle_activation_request(client, 'foobar')

        assert 'DEVICE_MODE_UNSUPPORTED' in str(res)

    @db_session
    def test_activation_time_bought(self, api_client, good_api_key):
        client = ClientCreator.create(api_client, good_api_key)
        with patch.object(
                    DeviceGetterService, 'get_device_from_client_and_activation_code_optional',
                    return_value=DeviceFactory.stub(ActiveUntil=datetime.now()+timedelta(days=1))), \
                patch.object(DeviceAPIService, 'sync_device_activation', return_value='PATCH_CODE'):
            res = handle_activation_request(client, 'foobar')
            patcher_3.stop()
        assert len(res) == 1
        assert 'ACTIVATION_REQUEST_SUCCESS' in str(res)
