from pony.orm import *
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from payg_loan_system.devices.services.device_delete_service import DeviceDeleteService
from shared.services.settings_service import SettingsService
from shared.logger.loggers import LogAPI
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIRequestService
from payg_loan_system.devices.model.device import Device, db
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
import config


class DeviceGlobalSyncService:
    SYNC_BLOCK_SIZE = 500

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
        owned_devices_SN_list = handler.list_devices()
        with db_session:
            cls._delete_unused_devices(api_name, owned_devices_SN_list)
        total_devices = len(owned_devices_SN_list)
        n = 1000
        device_blocks = [owned_devices_SN_list[i * n:(i + 1) * n] for i in range((total_devices + n - 1) // n)]
        for device_block in device_blocks:
            with db_session:
                cls._sync_block(api_name, device_block)
                flush()

    @classmethod
    def _sync_block(cls, api_name, device_block_raw):
        device_block = [str(device_sn) for device_sn in device_block_raw]
        existing_sns = select(device.SerialNumber for device in Device if device.type == api_name
                              and device.SerialNumber in device_block)[:]
        new_devices = list(set(device_block) - set(existing_sns))
        # We create only the new devices
        commit_count = 0
        for device_SN in new_devices:
            handler = DeviceAPIRequestService.get_device_api_helper(api_name)
            device_data = handler.get_device_data(device_SN)
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
