from datetime import datetime
from pony import orm
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.model.device_mode import DeviceMode
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIError
from payg_loan_system.requests.models import ActivationRequest
from payg_loan_system.offers.models import OfferType
from decimal import Decimal


SMS_KEYS = {
    DeviceMode.time: {
        'success': 'ACTIVATION_REQUEST_SUCCESS',
        'success_no_code': 'ACTIVATION_REQUEST_SUCCESS_NO_CODE',
        'no_credit': 'NO_ACTIVATION_TIME_ON_DEVICE'
    },
    DeviceMode.credit: {
        'success': 'CREDIT_ACTIVATION_REQUEST_SUCCESS',
        'success_no_code': 'CREDIT_ACTIVATION_REQUEST_SUCCESS_NO_CODE',
        'no_credit': 'NO_ACTIVATION_CREDIT_ON_DEVICE'
    }
}


@orm.db_session
def handle_activation_request(this_client, activation_request_code=None):
    # We get the device
    try:
        this_device = DeviceGetterService.get_device_from_client_and_activation_code_optional(
            this_client,
            activation_request_code
        )
    except DeviceAPIError as error:
        # We call the generic code error handler here to give a readable output
        return [handle_device_code_error(error)]
    except ConfigurationError as config_error:
        return [{'success': False,
                'status': 'CONFIGURATION_ERROR',
                'error_type': str(config_error)}]

    if not this_device.contract:
        return [{'success': False,
                'status': 'DEVICE_NOT_REGISTERED'}]
    return [sync_activation(this_device.contract, activation_request_code)]


def sync_activation(contract, activation_request_code=None, allow_negative=False, repayments=None):

    device = contract.linked_device

    if contract.status == ContractStatus.completed:
        return _autounlock(device, activation_request_code, repayments)

    hours, credit = None, None
    if device.Mode == DeviceMode.time:
        hours = device.get_remaining_activation_time_in_hours()
    elif device.Mode == DeviceMode.credit:
        credit = device.credit_balance if device.credit_balance else Decimal(0)
    else:
        return {
            'success': False,
            'status': 'DEVICE_MODE_UNSUPPORTED',
            'mode': device.get_mode_name()
        }

    if positive(hours) or positive(credit) or allow_negative:
        try:
            activation_code = DeviceAPIService.sync_device_activation(device, activation_request_code, repayments=repayments)
        except DeviceAPIError as error:
            return handle_device_code_error(error)

        if DeviceAPIService.device_requires_answer_code(device):
            return {
                'success': True,
                'status': SMS_KEYS[device.Mode]['success'],
                'activation_answer_code': activation_code,
                'expiration_time_day': device.ActiveUntil.strftime('%d') if device.ActiveUntil else None,
                'expiration_time_month': device.ActiveUntil.strftime('%m') if device.ActiveUntil else None,
                'expiration_time_year': device.ActiveUntil.strftime('%Y') if device.ActiveUntil else None,
                'credit_bought': credit,
                'credit_unit': device.contract.offer.credit_unit if device.contract else None,
                'contract_reference': device.contract.reference if device.contract else None,
            }
        create_activation_request(activation_request_code, device, time=hours, credit=round(credit) if credit else None)
        return {
            'success': True,
            'status': SMS_KEYS[device.Mode]['success_no_code'],
            'expiration_time_day': device.ActiveUntil.strftime('%d') if device.ActiveUntil else None,
            'expiration_time_month': device.ActiveUntil.strftime('%m') if device.ActiveUntil else None,
            'expiration_time_year': device.ActiveUntil.strftime('%Y') if device.ActiveUntil else None,
            'credit_bought': credit,
            'credit_unit': device.contract.offer.credit_unit if device.contract else None,
            'contract_reference': device.contract.reference if device.contract else None,
        }
    return {
        'success': False,
        'status': SMS_KEYS[device.Mode]['no_credit'],
        'expiration_time_day': device.ActiveUntil.strftime('%d') if device.ActiveUntil else None,
        'expiration_time_month': device.ActiveUntil.strftime('%m') if device.ActiveUntil else None,
        'expiration_time_year': device.ActiveUntil.strftime('%Y') if device.ActiveUntil else None,
        'contract_reference': device.contract.reference if device.contract else None,
    }

    


def _autounlock(device, request_code, repayments):
    if (device.contract.offer.automatic_unlock_code_sending or device.contract.offer.type == OfferType.lump_sum) and DeviceAPIService.device_can_auto_activate(device):
        device.Mode = DeviceMode.disabled
        try:
            registration_answer_code = DeviceAPIService.sync_device_settings(device, request_code, repayments)
            if DeviceAPIService.device_requires_answer_code(device):
                return {
                    'success': True, 'status': 'AUTO_DISABLE_PAYG_SUCCESS',
                    'registration_answer_code': registration_answer_code,
                    'contract_reference': device.contract.reference if device.contract else None,
                }
            return {
                'success': True, 'status': 'AUTO_DISABLE_PAYG_SUCCESS_NO_CODE',
                'contract_reference': device.contract.reference if device.contract else None,
            }
        except DeviceAPIError as error:
            return handle_device_code_error(error)
        except ConfigurationError as config_error:
            return {
                'success': False, 'status':
                'CONFIGURATION_ERROR', 'error_type': str(config_error)
            }
    return {
        'success': True, 'status': 'AUTO_DISABLE_PAYG_DISABLED'
    }


@orm.db_session
def create_activation_request(req_code, device, time=None, credit=None, debit_amt=0):
    if not req_code:
        req_code = str(device.composed_serial)
    return ActivationRequest(RequestCode=req_code,
                             ReceptionTime=datetime.now(),
                             Device=device,
                             client=device.contract.client.id,
                             TimeActivatedInHours=time,
                             CreditsAdded=credit,
                             DebitMade=int(debit_amt))


def pair_device(device, activation_request_code=None):
    if not device:
        return {
            'success': False,
            'status': 'DEVICE_NOT_FOUND'
        }
    
    try:
        pairing_code = DeviceAPIService.sync_device_activation(
            device,
            request_code=activation_request_code, 
            forced_expiration_time=None, 
            repayments=None,
            pair=True
        )
    except DeviceAPIError as error:
        return handle_device_code_error(error)
    except ConfigurationError as config_error:
        return {
            'success': False,
            'status': 'CONFIGURATION_ERROR',
            'error_type': str(config_error)
        }
    
    if DeviceAPIService.device_requires_answer_code(device):
        if pairing_code == "DEVICE_ALREADY_PAIRED":
            return {
                'success': True,
                'status': 'DEVICE_PAIRING_SUCCESS_NO_CODE',
                'contract_reference': device.contract.reference if device.contract else None,
                'device_serial': device.composed_serial,
            }
        else:
            return {
                'success': True,
                'status': 'DEVICE_PAIRING_SUCCESS',
                'pairing_answer_code': pairing_code,
                'contract_reference': device.contract.reference if device.contract else None,
                'device_serial': device.composed_serial,
            }
    
    return {
        'success': True,
        'status': 'DEVICE_PAIRING_SUCCESS_NO_CODE',
        'contract_reference': device.contract.reference if device.contract else None,
        'device_serial': device.composed_serial,
    }


def positive(x):
    return x and x > 0
