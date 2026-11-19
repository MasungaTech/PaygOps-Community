from mock import patch, Mock
from payg_loan_system.actions.switch_device_mode import handle_switch_device_mode
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.model.device_mode import DeviceMode
from payg_loan_system.contracts.models.contract_status import ContractStatus

REQUEST_CODE = 'OPT-TXT100000100'


def make_device(contract=None):
    return Mock(contract=contract, Mode=DeviceMode.time, get_display_name=Mock(return_value='TXT100000100'))


def make_user(can_access=True, can_access_in_all=True):
    return Mock(can_access=Mock(return_value=can_access), can_access_in_all=Mock(return_value=can_access_in_all))


@patch('payg_loan_system.actions.switch_device_mode.MentorRequest')
@patch.object(DeviceAPIService, 'sync_device_settings', return_value='743090462')
class TestSwitchDeviceMode:

    def test_disable_payg_on_unallocated_device(self, *args):
        device = make_device(contract=None)
        user = make_user()

        with patch.object(DeviceGetterService, 'get_device_from_registration_code', return_value=device):
            resp = handle_switch_device_mode(user, DeviceMode.disabled, REQUEST_CODE)

        assert resp == [{'success': True, 'status': 'DEVICE_DISABLE_PAYG',
                         'registration_answer_code': '743090462',
                         'device_serial': 'TXT100000100'}]
        assert device.Mode == DeviceMode.disabled
        user.can_access.assert_not_called()
        user.can_access_in_all.assert_any_call('ForcePAYGModeDevices')

    def test_disable_payg_on_unallocated_device_without_force_permission(self, *args):
        device = make_device(contract=None)
        user = make_user()
        user.can_access_in_all.side_effect = lambda permission: permission != 'ForcePAYGModeDevices'

        with patch.object(DeviceGetterService, 'get_device_from_registration_code', return_value=device):
            resp = handle_switch_device_mode(user, DeviceMode.disabled, REQUEST_CODE)

        assert resp == {'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'ForcePAYGModeDevices'}
        assert device.Mode == DeviceMode.time

    def test_disable_payg_on_allocated_device_with_active_contract(self, *args):
        contract = Mock(status=ContractStatus.active)
        device = make_device(contract=contract)
        user = make_user(can_access_in_all=False)

        with patch.object(DeviceGetterService, 'get_device_from_registration_code', return_value=device):
            resp = handle_switch_device_mode(user, DeviceMode.disabled, REQUEST_CODE)

        assert resp[0]['status'] == 'DEVICE_DISABLE_PAYG'
        user.can_access.assert_any_call('ForcePAYGModeDevices', person=contract.client.person)
        user.can_access_in_all.assert_not_called()
