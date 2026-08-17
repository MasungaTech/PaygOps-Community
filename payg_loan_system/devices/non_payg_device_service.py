from config import ENV_VAR
from pony import orm
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from constants import NON_PAYG_TYPE
from random import randint

from shared.logger.loggers import Error


class NonPAYGDeviceService:
    TIME_MODE = 1

    @classmethod
    def create_non_payg_device(cls, serial_number=None, product_sub_type=None):
        if serial_number:
            if Device.get(SerialNumber=str(serial_number), type=NON_PAYG_TYPE):
                raise Error('NPG_DEVICE_ALREADY_EXISTS')
        else:
            serial_number = cls._get_new_non_payg_device_serial()
            for i in range(0,5): # We try 5 times to generate a non-existing number
                if Device.get(SerialNumber=str(serial_number), type=NON_PAYG_TYPE):
                    serial_number = cls._get_new_non_payg_device_serial()
                else:
                    break
        this_new_device = DeviceCreateService.create(
            serial_number=str(serial_number),
            device_type=NON_PAYG_TYPE,
            mode=cls.TIME_MODE
        )
        if product_sub_type:
            pst = ProductSubType.get(lambda pst: pst.name == product_sub_type)
            if not pst:
                raise Error('Product sub-type {product_sub_type} does not exists', product_sub_type=product_sub_type)
            if not pst.device_type == 'NPG':
                raise Error('Product sub-type {product_sub_type} does not belongs to NPG device type', product_sub_type=product_sub_type)
            this_new_device.product_sub_type = pst
        return this_new_device

    @classmethod
    def _get_new_non_payg_device_serial(cls):
        import re
        if ENV_VAR != 'TEST': #POSTGRES syntax
            all_devices = orm.select(device for device in Device if device.type == NON_PAYG_TYPE).filter(lambda device: not orm.raw_sql('"device"."serialnumber" ~ \'[^0-9]\''))
        else: #SQLite syntax
            all_devices = orm.select(device for device in Device if device.type == NON_PAYG_TYPE).filter(lambda device: orm.raw_sql('cast("device"."serialnumber" AS bigint)'))

        last_device = all_devices.order_by(lambda d: orm.desc(orm.raw_sql('cast("device"."serialnumber" AS bigint)'))).first()
        if last_device:
            # We add a random number to reduce risk of collision if we have two requests at the same time
            new_serial = str(int(last_device.SerialNumber) + randint(1,10))
        else:
            new_serial = '1'
        return new_serial
