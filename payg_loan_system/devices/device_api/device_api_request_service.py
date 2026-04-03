from datetime import datetime
from shared.services.settings_service import SettingsService
from shared.api_helpers.client_helpers.api_helper_object import APIHelper, TestAPIHelper
from shared.api_helpers.client_helpers.api_exceptions import APIError
from shared.logger.loggers import LogAPI, Error
from shared.api_helpers.client_helpers import uuid_generation_helpers as api_helpers
from payg_loan_system.devices.device_api.device_api_errors import DeviceAPIError
from payg_loan_system.devices.model.token import Token
from payg_loan_system.devices.model.offline_token_model import TokenType
from payg_loan_system.devices.model.device_mode import DeviceMode
from messages_system.services.notifications_service import NotificationsService
from shared.helpers.date_helper import formatDateToUTCISODateStr
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
import config
import os
from core_system.core_entities import db


class DeviceAPIHelperBase:

    api_helper = None
    api_data = None

    def __init__(self, api_helper, api_data):
        self.api_helper = api_helper
        self.api_data = api_data

    @staticmethod
    def _result_or_error(result):
        if result is not None and 'error' in result:
            raise DeviceAPIError(result['error'])
        return result

    def _call(self, method, *args, **kwargs):
        try:
            return getattr(self.api_helper, method)(*args, **kwargs)
        except APIError as error:
            self._handle_api_error(error)

    def _get(self, *args, **kwargs):
        return self._call('get', *args, **kwargs)

    def _post(self, *args, **kwargs):
        return self._call('post', *args, **kwargs)

    def _put(self, *args, **kwargs):
        return self._call('put', *args, **kwargs)

    def _delete(self, *args, **kwargs):
        return self._call('delete', *args, **kwargs)

    @staticmethod
    def _cleanup_error_message(error):
        if isinstance(error, str):
            import re
            error = re.sub(r'no kit found with serial (\d+)', r'no kit found with serial [\1]', error)
        return error

    @staticmethod
    def _handle_api_error(error):
        logger = LogAPI()
        if type(error).__name__ == 'APINetworkingError':
            logger.Error('Device API Error: API_NETWORKING_ERROR')
            raise DeviceAPIError('API_NETWORKING_ERROR') from error
        elif type(error).__name__ == 'APIAuthorizationError':
            logger.Error('Device API Error: API_AUTHORIZATION_ERROR')
            raise DeviceAPIError('API_AUTHORIZATION_ERROR') from error
        elif type(error).__name__ == 'APIResourcePermissionError':
            logger.Error('Device API Error: INVALID_DEVICE_OWNER')
            raise DeviceAPIError('INVALID_DEVICE_OWNER') from error
        elif type(error).__name__ == 'APIInvalidInputError':
            error_data = error.args[0]
            raise DeviceAPIError(DeviceAPIHelperBase._cleanup_error_message(error_data['error'])) from error
        elif type(error).__name__ == 'APIRemoteServerError':
            logger.Error('Device API Error: REMOTE_SERVER_ERROR')
            raise DeviceAPIError('REMOTE_SERVER_ERROR') from error
        elif type(error).__name__ == 'HTTPError':
            if error.response:
                try:
                    if error.response.json()['error'] == 'DEVICE_DOES_NOT_EXIST':
                        logger.Error('Device API Error: DEVICE_DOES_NOT_EXIST')
                        raise DeviceAPIError('DEVICE_DOES_NOT_EXIST') from error
                except Exception as e:
                    pass # We raise the next one
        # We default to this if we dont know the exact nature of the error
        logger.Fatal(error)
        raise DeviceAPIError('API_ERROR', error) from error

    @classmethod
    def _get_sync_method_from_device_type(cls, device_type):
        api_type = SettingsService.get_setting('AllDeviceAPIS')[device_type].get('device_api_type')
        if api_type in config.SYNC_METHOD_CODES:
            return config.SYNC_METHOD_CODES[api_type]
        raise Exception('INVALID_DEVICE_SYNC_METHOD')

    def post_credit_update(self, device, data, request_code='', repayments=None):
        raise NotImplementedError

    def list_devices(self):
        raise NotImplementedError

    def get_device_data(self, serial_number):
        raise NotImplementedError

    def generate_offline_token(self, device, token_config):
        pass

    def list_supported_unit_types(self):
        return {"supported_credit_units": {}}

    def get_device_usage_metric_types(self, serial_number, force_sync=False):
        return []

    def get_device_usage_metric_data(self, serial_number, metric_type_uuid, last_metric_date):
        return []

    def subscribe_to_new_data_hook(self, device):
        pass

    def unsubscribe_from_new_data_hook(self, device):
        pass

    def supports_monitoring_data(self):
        return self.api_data.get('supports_monitoring_data', 'DISABLED') == 'ENABLED'

    def version(self):
        return self.api_data.get('device_api_version', 'v1')

    def get_device_state(self, device):
        pass


class DeviceAPIHelperV1(DeviceAPIHelperBase):

    DEVICES_ENDPOINT = 'devices/'
    ACTIVATION_SCOPE = 1
    SETTINGS_SCOPE = 2
    SETTINGS = {
        'client_id': 'clientId',
        'panel_size': 'panelSize',
        'batery_size': 'batterySize',
        'payg_mode': 'paygMode'
    }
    DATA_ADAPTER = {v: k for k,v in SETTINGS.items()}
    DATA_ADAPTER.update({'expirationDatetime': 'credit_value'})

    def post_credit_update(self, device, data, request_code='', repayments=None):
        self.set_device_data(device, data)
        scope = self.SETTINGS_SCOPE if set(data) - (set(data) - set(self.SETTINGS)) else self.ACTIVATION_SCOPE
        return self._sync_attempt(device, scope, request_code, repayments)

    def unlock_device(self, device, request_code=''):
        result = self._post(self.DEVICES_ENDPOINT + device.SerialNumber + '/unlock', data={
            'requestCode': request_code
        })
        if 'unlock_code' in result:
            return result['unlock_code']
        raise DeviceAPIError(result['error'])

    def set_device_data(self, device, data):
        formatted = {self.SETTINGS.get(k, k): data[k] for k in data}
        if 'credit_value' in data:
            formatted.update({'expirationDatetime': data['credit_value']})
        self._put(self.DEVICES_ENDPOINT + device.SerialNumber, data=formatted)

    def _sync_attempt(self, device, scope, request_code, repayments):
        result = self._post(self.DEVICES_ENDPOINT + device.SerialNumber + '/sync', data={
            "uuid": api_helpers.generate_uuid(),
            "sync_scope": scope,
            "sync_method": self._get_sync_method_from_device_type(device.type),
            "request_code": request_code
        }, timeout=90)
        if result.get('answer_code'):
            token_type = TokenType.disable_payg if device.Mode == DeviceMode.disabled else TokenType.add_credit
            this_token = Token(
                time=result.get('request_datetime', datetime.now()), uuid=result['uuid'], device=device,
                request_code=result.get('request_code') or '', token=result['answer_code'], sync_scope=result['sync_scope'],
                mode=device.Mode, expiration_time=device.ActiveUntil, token_type=token_type, credit_unit='ABSOLUTE_TIME',
                repayments=repayments or []
            )
            for rp in repayments or []:
                rp.processed = True
            add_hook_after_commit(db, 'token_generated', this_token.get_serialized_object())
            return result['answer_code']
        error = result.get('error', 'No token received')
        error = self._cleanup_error_message(error)
        NotificationsService.add_token_generation_error_notification(device, error)
        raise DeviceAPIError(error)

    def list_devices(self):
        result = self._get(self.DEVICES_ENDPOINT[:-1])
        return self._result_or_error(result)

    def list_credit_update(self, device): # TO DO: Should disappear (used in migration)
        if device.type == config.NON_PAYG_TYPE:
            return None
        result = self._get(self.DEVICES_ENDPOINT + device.SerialNumber + '/sync')
        return self._result_or_error(result)

    def get_device_from_code(self, code):
        result = self._get(self.DEVICES_ENDPOINT[:-1], params={'code': code})
        if not result:
            return None
        try:
            return str(result[0])
        except Exception as error:
            if 'error' in result:
                raise DeviceAPIError(result['error'])
            raise DeviceAPIError(value='Unknown Error', details=result)

    def get_device_data(self, serial_number):
        result = self._get(self.DEVICES_ENDPOINT + serial_number)
        formatted = {self.DATA_ADAPTER.get(k, k): result[k] for k in result}
        formatted.update({'supported_credit_units': ["ABSOLUTE_TIME", "DAYS"]})
        return self._result_or_error(formatted)

    def get_device_state(self, device):
        client_id = None
        panel_size = None
        battery_size = None
        if device.contract:
            client_id = device.contract.client.id
            panel_size = device.contract.offer.panel_size_in_w
            battery_size = device.contract.offer.battery_size_in_ah
        return {
            'client_id': client_id,
            'panel_size': panel_size,
            'batery_size': battery_size,
            'payg_mode': device.Mode,
            'credit_value': device.ActiveUntil or datetime.now()
        }


class DeviceAPIHelperV2(DeviceAPIHelperBase):

    CREDIT_UPDATES = 'credit_updates/'
    DEVICES_ENDPOINT = 'devices/'
    SUPPORTED_UNIT_TYPES_ENDPOINT = 'support/'
    DEVICE_METRIC_TYPES_ENDPOINT = 'devices/{}/metrics'
    DEVICE_METRIC_DATA_ENDPOINT = 'devices/{}/metrics/{}'
    DEVICE_NEW_DATA_HOOK_ENDPOINT = 'devices/{}/hooks/{}'

    def post_credit_update(self, device, data, request_code='', repayments=None):
        data.update({'device_serial_number': device.SerialNumber})
        request_uuid = api_helpers.generate_uuid()
        result = self._post(self.CREDIT_UPDATES + request_uuid, data=data, timeout=90)
        if result and 'token' in result:
            if not result['token']:
                result['token'] = 'NO_TOKEN'
            if 'uuid' not in result:
                result['uuid'] = request_uuid
            if data.get('status') == 'PENDING':
                return {
                    'uuid': result['uuid'],
                    'token': result['token'],
                    'credit_value': result['credit_value']
                }
            self._create_token_from_result(device, result, repayments)
            return result['token']
        NotificationsService.add_token_generation_error_notification(device, result.get('error', ''))
        return self._result_or_error(result)

    def list_devices(self):
        result = self._get(self.DEVICES_ENDPOINT[:-1])
        return self._result_or_error(result)
    
    def list_supported_unit_types(self):
        result = self._get(self.SUPPORTED_UNIT_TYPES_ENDPOINT[:-1])
        return self._result_or_error(result)

    def get_device_data(self, serial_number):
        result = self._get(self.DEVICES_ENDPOINT + serial_number)
        return self._result_or_error(result)

    def get_device_usage_metric_types(self, serial_number, force_sync=False):
        params = {'include_objects': 'true'}
        if force_sync:
            params.update({'force_sync': 'true'})
        result = self._get(self.DEVICE_METRIC_TYPES_ENDPOINT.format(serial_number), params=params)
        return self._result_or_error(result)

    def get_device_usage_metric_data(self, serial_number, metric_type_uuid, last_metric_date):
        result = self._get(self.DEVICE_METRIC_DATA_ENDPOINT.format(serial_number, metric_type_uuid),
                            params={'from': formatDateToUTCISODateStr(last_metric_date)})
        return self._result_or_error(result)

    def subscribe_to_new_data_hook(self, device):
        hook_uuid = api_helpers.generate_uuid()
        device.new_data_hook_uuid = hook_uuid
        data = {'url': config.PAYG_API_URL + config.API_PREFIX + '/devices/new_usage_data/' + hook_uuid}
        result = self._post(self.DEVICE_NEW_DATA_HOOK_ENDPOINT.format(device.SerialNumber, 'new_monitoring_data'), data=data)
        return self._result_or_error(result)

    def unsubscribe_from_new_data_hook(self, device):
        data = {'url': config.PAYG_API_URL + config.API_PREFIX + '/devices/new_usage_data/'+device.new_data_hook_uuid}
        device.new_data_hook_uuid = ""
        result = self._delete(self.DEVICE_NEW_DATA_HOOK_ENDPOINT.format(device.SerialNumber, 'new_monitoring_data'), data=data)
        return self._result_or_error(result)
    
    def generate_offline_token(self, device, token_config):
        return self.post_credit_update(device, data={
            'credit_value': token_config.credit_value,
            'credit_unit': token_config.unit,
            'credit_update_type': token_config.type,
            'status': 'PENDING'
        })

    def mark_offline_token_used(self, device, offline_token):
        data = {'status': 'COMMITTED', 'commit_time': offline_token.commit_time}
        result = self._put(self.CREDIT_UPDATES + offline_token.uuid, data=data)
        self._create_token_from_result(device, result)
        return result

    def set_device_data(self, device, data):
        raise Error('Option not available for this device.')

    def get_device_state(self, device):
        if device.Mode == DeviceMode.disabled:
            mode = 'DISABLE_PAYG'
        else:
            mode = 'SET_CREDIT'
        return {
            'credit_update_type': mode,
            'credit_value': device.ActiveUntil or datetime.now()
        }

    def _create_token_from_result(self, device, result, repayments=None):
        if result.get('effective_credit_update_type', None) == 'DISABLE_PAYG':
            value = None
        else:
            value = result.get('effective_credit_value', None)

        is_time = result.get('credit_unit') == 'ABSOLUTE_TIME'

        this_token = Token(
            time=result.get('time', datetime.now()),
            uuid=result['uuid'],
            device=device,
            request_code=result.get('request_code') or '',
            token=result['token'],
            mode=device.Mode,
            expiration_time=value if is_time else None,
            credit_value=value if not is_time else None,
            token_type=result.get('effective_credit_update_type', ''),
            credit_unit=result.get('credit_unit', ''),
            token_count=result.get('token_count', None),
            repayments=repayments or []
        )
        for rp in repayments or []:
            rp.processed = True
        add_hook_after_commit(db, 'token_generated', this_token.get_serialized_object())


class DeviceAPIRequestService:

    @classmethod
    def device_api_exists(cls, this_device_type):
        return this_device_type in SettingsService.get_setting('AllDeviceAPIS')

    @classmethod
    def get_device_api_helper(cls, device_type, data=None):
        device_api = data or SettingsService.get_setting('AllDeviceAPIS').get(device_type)
        if config.is_dev_mode() and not (device_type == 'LDC' or 'docker' in device_api.get('device_api_url')) and not os.getenv('ALLOW_LOCAL_DEVICE_CLOUD') == 'true': # LDC reserved in dev mode for local cloud tests
            api_helper = TestAPIHelper(device_type, device_api.get('device_api_version'))
        else:
            api_helper = APIHelper(device_api.get('device_api_url'), device_api.get('device_api_key'))
        if device_api.get('device_api_version') == "v2":
            return DeviceAPIHelperV2(api_helper, device_api)
        return DeviceAPIHelperV1(api_helper, device_api)
