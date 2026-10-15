from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService, DeviceAPIError
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.actions.swap_device import handle_device_change_request


class SwapDeviceSMSCommandService:
    registration_request_code_old = None
    registration_request_code_new = None

    @classmethod
    def process(cls, this_user, from_number, variables, reception_time=None, with_commission=False):
        if not cls._extract_variables(variables):
            return {'success': False,
                    'status': 'INVALID_USER_COMMAND',
                    'proper_command_syntax': 'CHANGEDEVICE# OldDeviceCode * NewDeviceCode'}

        # We get the old device from the registration code
        try:
            old_device = DeviceGetterService.get_device_from_registration_code(cls.registration_request_code_old)
        except DeviceAPIError as CE:
            return [handle_device_code_error(CE)]  # We call the generic code error handler to give a readable output
        except ConfigurationError as config_error:
            return {'success': False, 'status': 'CONFIGURATION_ERROR', 'error_type': str(config_error)}

        # We get the new device from the registration code
        try:
            new_device = DeviceGetterService.get_device_from_registration_code(cls.registration_request_code_new)
        except DeviceAPIError as CE:
            return [handle_device_code_error(CE)]  # We call the generic code error handler to give a readable output
        except ConfigurationError as config_error:
            return {'success': False, 'status': 'CONFIGURATION_ERROR', 'error_type': str(config_error)}

        if old_device.contract is None:
            return [{'success': False, 'status': 'DEVICE_NOT_REGISTERED'}]

        return handle_device_change_request(this_user, old_device.contract, new_device,
                                              cls.registration_request_code_old, cls.registration_request_code_new)

    @classmethod
    def _extract_variables(cls, variables_string):
        variables = variables_string.split('*')
        if len(variables) == 2:
            cls.registration_request_code_old = variables[0]
            cls.registration_request_code_new = variables[1]
            return True
        else:
            return False
