from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService, DeviceAPIError
from payg_loan_system.actions.deregister import handle_deregistration_request


class DeRegisterSMSCommandService:
    registration_request_code = None

    @classmethod
    def process(cls, this_user, from_number, variables, reception_time=None):
        if not cls._extract_variables(variables):
            return {'success': False,
                    'status': 'INVALID_USER_COMMAND',
                    'proper_command_syntax': 'DEREGISTER# DeviceCode'}

        try:
            cls.this_device = DeviceGetterService.get_device_from_registration_code(cls.registration_request_code)
        except DeviceAPIError as CE:
            return [handle_device_code_error(CE)]
        except ConfigurationError as config_error:
            return {'success': False,
                    'status': 'CONFIGURATION_ERROR',
                    'error_type': str(config_error)}

        status = handle_deregistration_request(this_user, cls.this_device, cls.registration_request_code)
        return status

    @classmethod
    def _extract_variables(cls, variables_string):
        variables = variables_string.split('*')
        if len(variables) == 1:
            cls.registration_request_code = variables[0]
            return True
        else:
            return False
