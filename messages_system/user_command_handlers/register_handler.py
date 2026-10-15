from payg_loan_system.actions.registration import register_lead
from sales_system.leads.models.lead import Lead
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService, DeviceAPIError


class RegisterSMSCommandService:
    registration_request_code = None
    lead_reference = None
    this_device = None
    this_lead = None

    @classmethod
    def process(cls, this_user, from_number, variables, reception_time=None):
        if not cls._extract_variables(variables):
            return {'success': False,
                    'status': 'INVALID_USER_COMMAND',
                    'proper_command_syntax': 'REGISTER# DeviceCode * LeadReference'}

        cls.this_lead = cls._get_lead()
        if cls.this_lead is None:
            return {'success': False,
                    'status': 'LEAD_REFERENCE_INVALID'}

        try:
            cls.this_device = DeviceGetterService.get_device_from_registration_code(cls.registration_request_code)
        except DeviceAPIError as CE:
            return [handle_device_code_error(CE)]
        except ConfigurationError as config_error:
            return {'success': False,
                    'status': 'CONFIGURATION_ERROR',
                    'error_type': str(config_error)}

        status = register_lead(this_user, cls.this_lead, cls.this_device, cls.registration_request_code)
        return status

    @classmethod
    def _extract_variables(cls, variables_string):
        variables = variables_string.split('*')
        if len(variables) == 2:
            cls.registration_request_code = variables[0]
            cls.lead_reference = variables[1].replace(' ', '').upper()
            return True
        else:
            return False

    @classmethod
    def _get_lead(cls):
        formatted_lead_reference = cls.lead_reference.upper().replace(' ', '')
        return Lead.get(future_contract_reference=formatted_lead_reference)
