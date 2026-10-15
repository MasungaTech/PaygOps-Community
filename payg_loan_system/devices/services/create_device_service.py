from datetime import datetime
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from shared.logger.loggers import Error
from pony.orm import db_session
from shared.services.celery_queue_service import CeleryQueueService
from stock_management_system.models import StockItem, StockMovement
from stock_management_system.stock_status import StockStatus
from payg_loan_system.devices.model.device import Device
from shared.services.settings_service import SettingsService
from worker_app.tasks.generate_offline_tokens import refresh_offline_tokens_for_device


class DeviceCreateService:

    @classmethod
    @db_session
    def create(cls, serial_number, device_type, mode, allowed_units=None, supports_monitoring_data=False, product_sub_type=None):

        if device_type not in SettingsService.get_setting('AllDeviceAPIS').keys() and device_type != 'NPG':
            raise Exception('UNKOWN_DEVICE_TYPE')

        # We remove the invisible characters from the string
        serial_number = ''.join(c for c in serial_number if c.isprintable())

        stock_item = StockItem()
        pst = None
        if product_sub_type:
            pst = ProductSubType.get(lambda pst: pst.name == product_sub_type and pst.device_type == device_type)
            if not pst:
                pst = ProductSubType(name=product_sub_type, device_type=device_type)
        device = Device(
            SerialNumber=serial_number,
            composed_serial=device_type + '-' + str(serial_number),
            type=device_type,
            Mode=mode,
            stock_item=stock_item,
            allowed_units=allowed_units or [],
            supports_monitoring_data=supports_monitoring_data,
            product_sub_type=pst
        )

        StockMovement(stock_item=stock_item,
                      date=datetime.now(),
                      destination_status=StockStatus.orphaned,
                      product_sub_type=stock_item.device.product_sub_type.id if stock_item.device and stock_item.device.product_sub_type else None)
        CeleryQueueService.execute_task(refresh_offline_tokens_for_device, device.id)
        return device
