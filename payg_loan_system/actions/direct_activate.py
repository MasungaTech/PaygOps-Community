from datetime import datetime, timedelta
from pony.orm import rollback
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.device_api.device_api_errors import DeviceAPIError
from payg_loan_system.devices.model.device_mode import DeviceMode


def handle_direct_activation_request(acting_user, this_device_serial, activation_request_code, time_in_days):

    # We get the device
    try:
        this_device = DeviceGetterService.get_device_from_serial_number_only(
            this_device_serial)
    except DeviceAPIError as CE:
        # We call the generic code error handler here to give a readable output
        return [handle_device_code_error(CE)]
    except ConfigurationError as config_error:
        return {'success': False,
                'status': 'CONFIGURATION_ERROR',
                'error_type': str(config_error)}

    if this_device.Mode == DeviceMode.disabled:
        return {'success': False,
                'status': 'DEVICE_MODE_UNSUPPORTED',
                'mode': 'PAYG Disabled'}

    if not acting_user.can_access_in_any('GiveDelayOver2DaysActions'):
        if time_in_days > 2:
            return {'success': False, 'status': 'INSUFFICIENT_PERMISSION', 'permission': 'GiveDelayOver2DaysActions'}

    new_expiration_time = datetime.now()+timedelta(days=time_in_days)

    try:
        ActivationCode = DeviceAPIService.sync_device_activation(this_device,
                                                                 activation_request_code,
                                                                 new_expiration_time)
    except DeviceAPIError as CE:
        # We call the generic code error handler here to give a readable output
        return [handle_device_code_error(CE)]

    if DeviceAPIService.device_requires_answer_code(this_device):
        return {
            'success': True,
            'status': 'ACTIVATION_REQUEST_SUCCESS',
            'contract_reference': this_device.contract.reference if this_device.contract else '',
            'activation_answer_code': ActivationCode,
            'expiration_time_day': new_expiration_time.strftime('%d'),
            'expiration_time_month': new_expiration_time.strftime('%m'),
            'expiration_time_year': new_expiration_time.strftime('%Y'),
        }
    else:
        return {
            'success': True,
            'status': 'ACTIVATION_REQUEST_SUCCESS_NO_CODE',
            'contract_reference': this_device.contract.reference if this_device.contract else '',
            'expiration_time_day': new_expiration_time.strftime('%d'),
            'expiration_time_month': new_expiration_time.strftime('%m'),
            'expiration_time_year': new_expiration_time.strftime('%Y'),
        }
