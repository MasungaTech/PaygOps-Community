from pony.orm import *
import time
from payg_loan_system.devices.services.device_delete_service import DeviceDeleteService
from shared.services.settings_service import SettingsService
from shared.logger.loggers import LogAPI
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIHelperBase, DeviceAPIRequestService
from payg_loan_system.devices.model.device import Device, db
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
import config


class DeviceGlobalSyncService:
    SYNC_BLOCK_SIZE = 100

    @classmethod
    def sync_all_new_owned_devices(cls):
        # For all device APIs
        for api_name in SettingsService.get_setting('AllDeviceAPIS'):
            if config.is_dev_mode() and config.ENV_VAR != 'TEST' and api_name != 'LDC':
                continue
            try:
                cls.sync_owned_device_from_specific_api(api_name)
            except Exception as exception:
                LogAPI.FatalNoRequest(exception)

    @classmethod
    def sync_owned_device_from_specific_api(cls, api_name):
        handler = DeviceAPIRequestService.get_device_api_helper(api_name)
        listed_devices = handler.list_devices(include_objects=True, page_size=cls.SYNC_BLOCK_SIZE)
        owned_devices_SN_list, device_data_by_sn = cls._serials_and_data_from_list(listed_devices)
        with db_session:
            cls._delete_unused_devices(api_name, owned_devices_SN_list)
        total_devices = len(owned_devices_SN_list)
        n = 1000
        device_blocks = [owned_devices_SN_list[i * n:(i + 1) * n] for i in range((total_devices + n - 1) // n)]
        for device_block in device_blocks:
            with db_session:
                cls._sync_block(api_name, device_block, device_data_by_sn)
                flush()

    @staticmethod
    def _serials_and_data_from_list(listed_devices):
        serials = []
        device_data_by_sn = {}
        for item in listed_devices or []:
            if isinstance(item, dict):
                serial = DeviceAPIHelperBase.device_list_key(item)
                if not serial:
                    continue
                serials.append(serial)
                if 'payg_mode' in item or 'paygMode' in item:
                    device_data_by_sn[serial] = item
            else:
                serials.append(str(item))
        return serials, device_data_by_sn

    @classmethod
    def _sync_block(cls, api_name, device_block_raw, device_data_by_sn=None):
        device_data_by_sn = device_data_by_sn or {}
        device_block = [str(device_sn) for device_sn in device_block_raw]
        existing_sns = select(device.SerialNumber for device in Device if device.type == api_name
                              and device.SerialNumber in device_block)[:]
        new_devices = list(set(device_block) - set(existing_sns))
        # We create only the new devices
        commit_count = 0
        handler = DeviceAPIRequestService.get_device_api_helper(api_name)
        for device_SN in new_devices:
            device_data = cls._device_data_for_create(handler, device_SN, device_data_by_sn.get(device_SN))
            DeviceCreateService.create(
                serial_number=device_SN,
                device_type=api_name,
                mode=int(device_data['payg_mode']),
                allowed_units=device_data.get('supported_credit_units', []),
                supports_monitoring_data=device_data.get('supports_monitoring_data'),
                product_sub_type=device_data.get('model')
            )
            # We commit once in a while so that the user can see progress when they refresh the page
            commit_count += 1
            if commit_count >= 50:
                commit_count = 0
                commit()

    @staticmethod
    def _device_data_for_create(handler, device_sn, device_data):
        if isinstance(device_data, dict):
            if 'payg_mode' not in device_data and 'paygMode' in device_data:
                device_data = dict(device_data)
                device_data['payg_mode'] = device_data['paygMode']
            if 'payg_mode' in device_data:
                return device_data
        time.sleep(0.1)
        return handler.get_device_data(device_sn)

    @classmethod
    def update_device_parameters(cls, device):
        handler = DeviceAPIRequestService.get_device_api_helper(device.type)
        device_data = handler.get_device_data(str(device.SerialNumber))
        device.allowed_units=device_data.get('supported_credit_units', [])
        device.supports_monitoring_data=device_data.get('supports_monitoring_data')

    @classmethod
    def _delete_unused_devices(cls, api_name, owned_devices_SN_list):
        owned_devices_SN_list = [str(device_sn) for device_sn in owned_devices_SN_list]
        removed = select(d for d in Device if d.type == api_name and d.SerialNumber not in owned_devices_SN_list)[:]
        for device in removed:
            try:
                # We skip the audit log here because it's automated
                DeviceDeleteService.delete_from_object_and_user(device, user=None, skip_log=True)
            except Exception as e:
                LogAPI.Event("Could not delete device "+str(device.id)+" / "+str(device.composed_serial)+": "+str(e))

    @classmethod
    def get_last_sync(cls):
        stock_movements = select((movement.date.date(), count(movement)) for movement in db.StockMovement
                                 if not movement.previous)
        return stock_movements
