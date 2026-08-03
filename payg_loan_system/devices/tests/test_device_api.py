from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIHelperV1, DeviceAPIRequestService
from payg_loan_system.devices.device_api.device_api_sync_service import DeviceGlobalSyncService
from pony import orm
from payg_loan_system.devices.model.device import Device
from shared.services.settings_service import SettingsService

class TestDeviceApi():
    
    @orm.db_session
    def test_sync_owned_device(self):
        apis = SettingsService.get_setting('AllDeviceAPIS').keys()
        #devices we get from all device clouds
        all_from_cloud = []
        for api in apis:
            handler = DeviceAPIRequestService.get_device_api_helper(api)
            from_cloud = handler.list_devices()
            all_from_cloud.extend(from_cloud)
        all_from_cloud = [str(sn) for sn in all_from_cloud]
        can_not_delete  = orm.select(d.SerialNumber for d in Device 
                            if d.contract is not None
                            or d.allocated_lead is not None
                            or d.ActiveUntil is not None
                            or d.addon is not None
                            or orm.count(d.ActivationRequests) != 0 
                            or orm.count(d.MentorRequests) != 0 
                            or orm.count(d.transaction_requests) != 0)[:]
        DeviceGlobalSyncService.sync_all_new_owned_devices()
        after_sync = [str(d.SerialNumber) for d in Device.select()]
        #make sure devices that can't be deleted are left after sync
        assert all(device in after_sync for device in can_not_delete) == True
        #make sure everything was added
        assert all(serial in after_sync for serial in all_from_cloud) == True
        assert (len(can_not_delete) + len(all_from_cloud)) == len(after_sync)
