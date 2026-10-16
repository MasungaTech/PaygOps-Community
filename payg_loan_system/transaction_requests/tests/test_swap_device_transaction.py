import uuid
import json
from pony.orm import db_session
from payg_loan_system.transaction_requests.services.swap_device_service import \
    SwapDeviceTransactionService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator


class TestSwapDeviceTransation:

    @db_session
    def test_swap_device_transaction(self, api_client, good_api_key):

        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        old_device = client.contracts.select().first().linked_device
        new_device = ClientCreator.create_device({"serial_number": "TSWAPINGDEVICE"})
        request = SwapDeviceTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            old_device_serial=old_device.composed_serial,
            new_device_serial=new_device.composed_serial,
            old_request_code=None,
            new_request_code=None
        )
        print(request.to_dict())
        assert request.type == 'swap_device'
        assert json.loads(request.request_data) == {
            'old_device_serial': old_device.composed_serial,
            'new_device_serial': new_device.composed_serial,
            'old_request_code': None,
            'new_request_code': None,
            'note': None,
            'send_sms_to_client': False
        }

        assert json.loads(request.answer_data)[0]['status'] == 'DEVICE_CHANGE_SUCCESS_NO_CODE'
        assert request.user == user
        assert request.success == True
        assert request.client == client
        assert request.device == None
