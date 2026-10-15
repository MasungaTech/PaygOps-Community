from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService, DeviceAPIError
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.actions.collect_cash import handle_paycash_request
from decimal import Decimal


class CollectCashSMSCommandService:
    registration_request_code = None
    amount = None

    @classmethod
    def process(cls, this_user, from_number, variables, reception_time=None, with_commission=False):
        if not cls._extract_variables(variables):
            return {'success': False,
                    'status': 'INVALID_USER_COMMAND',
                    'proper_command_syntax': 'PAYCASH# DeviceCode * Amount'}

        try:
            cls.amount = Decimal(cls.amount)
        except Exception:
            return {'success': False,
                    'status': 'INVALID_NUMBER_FORMAT'}

        # We get the device from the registration code
        try:
            this_device = DeviceGetterService.get_device_from_registration_code(cls.registration_request_code)
        except DeviceAPIError as CE:
            return [handle_device_code_error(CE)]  # We call the generic code error handler to give a readable output
        except ConfigurationError as config_error:
            return {'success': False, 'status': 'CONFIGURATION_ERROR', 'error_type': str(config_error)}

        paying_client = this_device.contract.client if this_device.contract else None
        if this_device.contract is None:
            return {'success': False, 'status': 'DEVICE_NOT_REGISTERED'}

        if with_commission:
            commission = 1000
        else:
            commission = 0

        status = handle_paycash_request(this_user, cls.amount, this_device=this_device,
                                        commission=commission, registration_request_code=cls.registration_request_code)
        return status

    @classmethod
    def _extract_variables(cls, variables_string):
        variables = variables_string.split('*')
        if len(variables) == 2:
            cls.registration_request_code = variables[0]
            cls.amount = variables[1]
            return True
        else:
            return False
