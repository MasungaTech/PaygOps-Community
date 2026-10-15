from payg_loan_system.devices.model.device import Device
from pony import orm
from stock_management_system.services.stock_item_getter_service import StockItemGetterService
from shared.logger.loggers import LogAPI

logger = LogAPI()


class DeviceListService:

    @classmethod
    def get_non_used_devices_for_user_list(cls, user, offer=None, add_on_offer=None):
        all_stock_items_for_user = StockItemGetterService.get_list(user, for_sale=True) # This should filter installed devices and reserved ones already
        devices = orm.select(device for device in Device if device.stock_item in all_stock_items_for_user)
        non_used_devices = devices.filter(lambda device: device.contract is None and device.addon is None and device.allocated_lead is None)

        if offer and offer.device_type:
            non_used_devices = non_used_devices.filter(lambda d: d.type == offer.device_type)
        if add_on_offer and add_on_offer.product_type:
            non_used_devices = non_used_devices.filter(lambda d: d.type == add_on_offer.product_type)

        if offer and offer.product_sub_type:
            non_used_devices = devices.filter(lambda d: d.product_sub_type == offer.product_sub_type)
        if add_on_offer and add_on_offer.product_sub_type:
            non_used_devices = devices.filter(lambda d: d.product_sub_type == add_on_offer.product_sub_type)

        return non_used_devices

    @classmethod
    def get_devices_from_client(cls, this_client):
        all_devices = orm.select(device for device in Device if device.contract.client == this_client)
        return all_devices

    @classmethod
    def get_used_and_unused_devices(cls, user, contract_ids, lead_ids):
        unused_devices = orm.select(d.id for d in cls.get_non_used_devices_for_user_list(user))[:]
        used_devices = orm.select(d.id for d in Device if d.contract.id in contract_ids)[:]
        lead_devices = orm.select(d.id for d in Device if d.allocated_lead.id in lead_ids)[:]
        all_devices = Device.select(lambda d: d.id in used_devices+unused_devices+lead_devices)
        return all_devices

    @classmethod
    def get_devices_in_use_that_support_usage_monitoring(cls):
        devices = orm.select(device for device in Device if (device.contract is not None or orm.count(device.metrics) > 0) and device.supports_monitoring_data)
        return devices

   