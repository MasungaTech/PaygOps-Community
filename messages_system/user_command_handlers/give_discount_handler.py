from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService, DeviceAPIError
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.offers.models import OfferType
from payg_loan_system.actions.give_discount import give_discount


class GiveDiscountSMSCommandService:
    registration_request_code = None
    discounted_days = None

    @classmethod
    def process(cls, this_user, from_number, variables, reception_time=None, with_commission=False):
        if not cls._extract_variables(variables):
            return {'success': False,
                    'status': 'INVALID_USER_COMMAND',
                    'proper_command_syntax': 'GIVEDISCOUNT# DeviceCode * NumberOfDays'}

        try:
            cls.discounted_days = int(cls.discounted_days)
        except ValueError:
            return {'success': False,
                    'status': 'INVALID_NUMBER_FORMAT'}

        # We get the device from the registration code
        try:
            this_device = DeviceGetterService.get_device_from_registration_code(cls.registration_request_code)
        except DeviceAPIError as CE:
            return [handle_device_code_error(CE)]  # We call the generic code error handler to give a readable output
        except ConfigurationError as config_error:
            return {'success': False, 'status': 'CONFIGURATION_ERROR', 'error_type': str(config_error)}

        this_client = this_device.contract.client if this_device.contract else None
        if this_client is None:
            return {'success': False, 'status': 'DEVICE_NOT_REGISTERED'}
        discounted_units = cls.discounted_days
        status = give_discount(acting_user=this_user,
                               discounted_units=discounted_units,
                               this_device=this_device,
                               registration_request_code=cls.registration_request_code)

        return status

    @classmethod
    def _extract_variables(cls, variables_string):
        variables = variables_string.split('*')
        if len(variables) == 2:
            cls.registration_request_code = variables[0]
            cls.discounted_days = variables[1]
            return True
        else:
            return False
