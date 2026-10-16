from payg_loan_system.devices.model.offline_token_model import OfflineToken, OfflineTokenConfig
from shared.helpers.date_helper import parse_datetime
from shared.services.base_getter_service import BaseGetterService
from shared.services.settings_service import SettingsService
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIRequestService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from pony import orm
from constants import NON_PAYG_TYPE


class OfflineTokenService(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        return OfflineToken.select()

    @classmethod
    def generate_tokens_for_applicable_devices(cls, offer=None, device_type=None, user=None):
        from payg_loan_system.devices.model.device import Device
        compatible_types = cls.get_compatible_device_types()
        all_devices = orm.select(device for device in Device if device.type in compatible_types)
        if offer:
            all_devices = all_devices.filter(lambda d: d.contract and d.contract.offer == offer)
        if device_type:
            all_devices = all_devices.filter(lambda d: d.type == device_type)
        if user:
            all_devices = all_devices.filter(lambda d: d.stock_item and d.stock_item.user == user)
        for device in all_devices:
            cls.commit_and_generate_new(device)

    @classmethod
    def get_compatible_device_types(cls):
        compatible_types = []
        device_types = SettingsService.get_setting('AllDeviceAPIS')
        for device_type in device_types:
            if cls.is_type_compatible(device_type):
                compatible_types.append(device_type)
        return compatible_types

    @classmethod
    def is_type_compatible(cls, device_type):
        if device_type == NON_PAYG_TYPE:
            return False
        device_type_data = SettingsService.get_setting('AllDeviceAPIS').get(device_type)
        if device_type_data.get('offline_mode') == 'ENABLED' and device_type_data.get('device_api_version') == "v2":
            return True
        return False

    @classmethod
    def should_generate_token_for_device(cls, device):
        return (device.contract and device.contract.status == ContractStatus.active) or device.stock_item.user

    @classmethod
    def generate_for_device_if_needed(cls, device):
        if cls.is_type_compatible(device.type):
            cls.commit_and_generate_new(device)

    @classmethod
    def commit_and_generate_new(cls, device):
        cls.commit_pending_tokens(device)
        if cls.should_generate_token_for_device(device):
            cls.generate_tokens_for_device(device)

    @classmethod
    def commit_pending_tokens(cls, device):
        handler = cls._get_handler(device)
        used_tokens = device.offline_tokens.filter(lambda t: t.used and not t.marked)
        for token in used_tokens:
            handler.mark_offline_token_used(device, offline_token=token)
        # We clear up any remaining tokens (in the future we might need to check which to delete)
        for token in device.offline_tokens.filter(lambda t: not (t.deleted or t.used)):
            token.deleted = True

    @classmethod
    def generate_tokens_for_device(cls, device):
        handler = cls._get_handler(device)
        if device.contract:
            tk_configs = device.contract.offer.offline_token_configs
        else:
            tk_configs = OfflineTokenConfig.select(lambda c: c.device_type == device.type)

        # We generate the new ones
        for tk_config in tk_configs:
            token = handler.generate_offline_token(device, tk_config)
            device.offline_tokens.create(
                uuid=token['uuid'],
                token=token['token'],
                type=tk_config.type,
                credit_value=token['credit_value'],
                unit=tk_config.unit
            )

    @classmethod
    def _get_handler(cls, device):
        return DeviceAPIRequestService.get_device_api_helper(device.type)
    
    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids, **kwargs):
        if 'contract' not in cached_ids:
            relevant_clients_ids = cached_ids['client']
            contracts = current_user.get_relevant_contracts_for_mobile(relevant_clients_ids)
            cached_ids['contract'] = orm.select(e.id for e in contracts)[:]
        if current_user.can_access_in_any('GiveTokensOfflineActions'):
            relevant_devices = current_user.get_devices_for_mobile(cached_ids['contract'])
            relevant_devices = relevant_devices.filter(lambda d: d.stock_item.user == current_user or d.contract is not None)
            return OfflineToken.select(lambda t: t.device in relevant_devices and not t.deleted and not t.used)
        return OfflineToken.select(lambda t: t.id == -1)
    
    @classmethod
    def _edit_from_data_and_user(cls, entity, data, user):
        used = data.get('used', None)
        if used:
            entity.used = used
            entity.commit_time = parse_datetime(data.get('commit_time'))
        return entity
