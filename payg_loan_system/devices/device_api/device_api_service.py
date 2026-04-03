from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIRequestService
from payg_loan_system.devices.model.offline_token_model import TokenType
from payg_loan_system.devices.model.device_mode import DeviceMode
from config import NON_PAYG_TYPE, NON_PAYG_IDENTIFIER, AVAILABLE_SUPPORTED_OFFER_TYPES, TIME_BASED_UNITS
from shared.logger.loggers import Error
from shared.services.celery_queue_service import CeleryQueueService
from shared.services.settings_service import SettingsService
from worker_app.tasks.generate_offline_tokens import refresh_offline_tokens_for_device
from payg_loan_system.devices.services.offline_token_service import OfflineTokenService
import config
from datetime import datetime
from pony import orm


class DeviceAPIService:

    @classmethod
    def sync_device_activation(cls, this_device, request_code=None, forced_expiration_time=None, repayments=None, pair=False):
        credit_update_type = TokenType.pair_device if pair else TokenType.add_credit
        data = {'credit_update_type': credit_update_type}
        if this_device.Mode == DeviceMode.credit:
            data.update({
                'credit_value': this_device.credit_balance,
                'credit_unit': this_device.credit_unit
            })
        elif this_device.Mode == DeviceMode.time:
            data.update({'credit_value': forced_expiration_time or this_device.ActiveUntil})
        result = cls._sync(this_device, data, request_code, repayments)
        if this_device.Mode == DeviceMode.credit:
            this_device.credit_balance = 0
        return result


    @classmethod
    def sync_device_settings(cls, this_device, request_code=None, repayments=None):
        if SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device' and not this_device:
            return NON_PAYG_IDENTIFIER
        if SettingsService.get_setting('ContractDeviceRestrictions') != 'no_device' and not this_device:
            return NON_PAYG_IDENTIFIER
        if SettingsService.get_setting('ContractDeviceRestrictions') != 'no_device' and this_device:
            data = cls._get_device_state(this_device)
            token_type = TokenType.disable_payg if this_device.Mode == DeviceMode.disabled else TokenType.add_credit
            data.update({
                'credit_update_type': token_type
            })
            return cls._sync(this_device, data, request_code, repayments)

    @classmethod
    def _sync(cls, device, data, request_code, repayments=None):
        if device.type == NON_PAYG_TYPE:
            return NON_PAYG_IDENTIFIER
        clean_code = cls._get_clean_code(device, request_code)
        handler = DeviceAPIRequestService.get_device_api_helper(device.type)
        result = handler.post_credit_update(device, data=data, request_code=clean_code, repayments=repayments)
        cls.subscribe_or_unsubscribe_to_new_data_hook(device)
        CeleryQueueService.execute_task(refresh_offline_tokens_for_device, device.id)
        return result

    @classmethod
    def subscribe_or_unsubscribe_to_new_data_hook(cls, device):
        handler = DeviceAPIRequestService.get_device_api_helper(device.type)
        if handler.supports_monitoring_data():
            if device.contract is not None and device.supports_monitoring_data is not False and not device.new_data_hook_uuid:
                handler.subscribe_to_new_data_hook(device)
            if device.contract is None and device.supports_monitoring_data is not False and device.new_data_hook_uuid is not None:
                handler.unsubscribe_from_new_data_hook(device)

    @classmethod
    def update_device_state(cls, this_device):
        if this_device.type != NON_PAYG_TYPE:
            handler = DeviceAPIRequestService.get_device_api_helper(this_device.type)
            handler.set_device_data(this_device, data=cls._get_device_state(this_device))

    @classmethod
    def get_available_unit_types_for_device_type(cls, device_type, data=None):
        if device_type == NON_PAYG_TYPE:
            return {}
        handler = DeviceAPIRequestService.get_device_api_helper(device_type, data)
        result = handler.list_supported_unit_types() or {}
        supported_units = result.get('supported_credit_units', {})
        # We support some legacy device clouds that used list instead of dict
        if isinstance(supported_units, list):
            supported_units = {u:u for u in supported_units}
        return supported_units

    @classmethod
    def get_available_unit_types_per_device_type(cls):
        available_device_types = cls.get_device_types_and_type_names()
        available_unit_types = {}
        for device_type in available_device_types:
            available_unit_types[device_type] = cls.get_available_unit_types_for_device_type(device_type)
        return available_unit_types
    
    @classmethod
    def device_type_support_usage_based(cls, device_type):
        config_all = SettingsService.get_setting('AllDeviceAPIS')
        config = config_all.get(device_type)
        if config:
            supported_units = config.get('supported_units', {})
            # This is a workaround for legacy device clouds that used list instead of dict
            if isinstance(supported_units, list):
                supported_units = {u:u for u in supported_units}
                config_all[device_type]['supported_units'] = supported_units
                SettingsService.set_setting('AllDeviceAPIS', config_all)
                orm.commit()
            no_time_units = set(supported_units.keys())-set(TIME_BASED_UNITS)
            return bool(no_time_units)
        return False

    @classmethod
    def get_available_offer_types_per_device_type(cls):
        just_time = {"TIME_BASED": AVAILABLE_SUPPORTED_OFFER_TYPES["TIME_BASED"]}
        apis = SettingsService.get_setting('AllDeviceAPIS')
        return {k: AVAILABLE_SUPPORTED_OFFER_TYPES if cls.device_type_support_usage_based(k) else just_time for k in apis}

    @classmethod
    def get_usage_metrics_data_for_device(cls, this_device, metric_type_uuid, last_metric_date):
        handler = DeviceAPIRequestService.get_device_api_helper(this_device.type)
        return handler.get_device_usage_metric_data(this_device.SerialNumber, metric_type_uuid, last_metric_date)

    @classmethod
    def get_usage_metric_types_for_device(cls, this_device, force_sync=False):
        handler = DeviceAPIRequestService.get_device_api_helper(this_device.type)
        if not handler.supports_monitoring_data():
            return []
        return handler.get_device_usage_metric_types(this_device.SerialNumber, force_sync=force_sync)

    @classmethod
    def _get_device_state(cls, device):
        if device.type == NON_PAYG_TYPE:
            return {}
        handler = DeviceAPIRequestService.get_device_api_helper(device.type)
        return handler.get_device_state(device)

    @classmethod
    def unlock_device(cls, this_device, request_code=None):
        if this_device.type == NON_PAYG_TYPE:
            return NON_PAYG_IDENTIFIER
        handler = DeviceAPIRequestService.get_device_api_helper(this_device.type)
        return handler.unlock_device(this_device, request_code)

    @staticmethod
    def _api_type_of(device):
        return SettingsService.get_setting('AllDeviceAPIS').get(device.type).get('device_api_type')

    @classmethod
    def device_can_auto_activate(cls, this_device):
        if not this_device:
            return False
        return True if this_device.type == NON_PAYG_TYPE else cls._api_type_of(this_device) != "TWO_WAY_CODE"

    @classmethod
    def device_requires_answer_code(cls, this_device):
        # return False if this_device.type == NON_PAYG_TYPE else cls._api_type_of(this_device) != "GSM"
        if SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device' and not this_device:
            return False
        if SettingsService.get_setting('ContractDeviceRestrictions') in ['require_device', 'both'] and not this_device:
            return False
        if SettingsService.get_setting('ContractDeviceRestrictions') in ['require_device', 'both'] and this_device:
            return False if this_device.type == NON_PAYG_TYPE else cls._api_type_of(this_device) != "GSM"

    @classmethod
    def device_requires_request_code(cls, this_device):
        return False if this_device.type == NON_PAYG_TYPE else cls._api_type_of(this_device) == 'TWO_WAY_CODE'

    @classmethod
    def get_device_types_and_type_names(cls, include_data_attributes=False, include_any=False, exclude_time_units=False):
        device_types = {}
        if SettingsService.get_setting('NPGDeviceEnabled'):
            if not include_data_attributes:
                device_types = {NON_PAYG_TYPE: 'Non-PAYG Device (NPG)'}
            else:
                device_types = {NON_PAYG_TYPE: {
                    'value': 'Non-PAYG Device (NPG)', 
                    'offline_enabled': False,
                    'supported_offer_type': 'BOTH'
                }}
        if include_any:
            if not include_data_attributes:
                device_types.update({'Any': 'Any'})
            else:
                device_types.update({'Any': {
                    'value': 'Any', 
                    'offline_enabled': True,
                    'supported_offer_type': 'TIME_BASED'
                }})
        devices_api = SettingsService.get_setting('AllDeviceAPIS')
        if not include_data_attributes:
            device_types.update({t: cls.get_device_human_readable_type_name(t) for t in devices_api})
        else:
            device_types.update({t: {
                'value': cls.get_device_human_readable_type_name(t),
                'offline_enabled': OfflineTokenService.is_type_compatible(t),
                'supported_offer_type': devices_api[t].get('supported_offer_type', 'TIME_BASED'),
                'supported_units': devices_api[t].get('supported_units', {}) if not exclude_time_units \
                    else {k:v for k,v in devices_api[t].get('supported_units', {}).items() if not k in config.TIME_BASED_UNITS} 
            } for t in devices_api})
        device_types = dict(sorted(device_types.items()))
        return device_types


    @classmethod
    def get_device_human_readable_type_name(cls, device_type):
        if device_type == NON_PAYG_TYPE:
            return 'Non-PAYG Device (NPG)'
        devices_api = SettingsService.get_setting('AllDeviceAPIS')
        if 'device_api_full_name' in devices_api[device_type]:
            return devices_api[device_type]['device_api_full_name']+' ('+device_type+')'
        return device_type

    @classmethod
    def validate_device_type(cls, device_type):
        """Validate if a device type exists in the available device types."""
        if not device_type or device_type == 'Any':
            return True
        available_device_types = cls.get_device_types_and_type_names(include_any=False)
        return device_type in available_device_types

    @classmethod
    def _get_clean_code(cls, device, composed_code):
        if not cls.device_requires_request_code(device) or not composed_code:
            return None
        clean_code, device_type = cls.get_code_and_type_from_composed_code(composed_code)
        return clean_code
    
    @classmethod
    def get_code_and_type_from_composed_code(cls, composed_code):
        if not composed_code:
            raise Error('Serial Number not provided')
        fallback_device_type = SettingsService.get_setting('FallBackDeviceType')
        if '-' in composed_code:
            split_composed_code = composed_code.split('-')
            device_type = split_composed_code[0].upper()
            code = '-'.join([a for a in split_composed_code[1:]]) # We join the remaining parts
            if DeviceAPIRequestService.device_api_exists(device_type) or device_type == NON_PAYG_TYPE:
                return code, device_type
        # If there's no '-' or it's not a known type, we assume it's an fallback type SN
        if fallback_device_type == 'DISABLED':
            raise Error('DEVICE_TYPE_NOT_SPECIFIED')
        return composed_code, fallback_device_type
    

   