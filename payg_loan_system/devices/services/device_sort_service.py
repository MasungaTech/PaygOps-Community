from datetime import datetime
from shared.services.sorter import Sorter
from payg_loan_system.devices.model.device import Device
from pony import orm


class DeviceSorter(Sorter):
    def sort_by(field_name):
        options = {
            'serial_number': DeviceSorter.by_serial_number,
            'active_until': DeviceSorter.by_active_until,
            'owner': DeviceSorter.by_owner,
            'type': DeviceSorter.by_type,
            'offer': DeviceSorter.by_offer,
            'mode': DeviceSorter.by_mode,
        }

        return options.get(field_name, DeviceSorter.by_serial_number)

    def real_field_sort(field_name, desc=False):
        options = {
            'serial_number': Device.SerialNumber,
            'active_until': Device.ActiveUntil,
            'owner': lambda d: d.contract.client.person.name,
            'type': Device.type,
            'offer': False,
            'mode': Device.Mode,
            'contract': lambda d: d.contract.reference,
        }
        options_desc = {
            'owner': lambda d: orm.desc(d.contract.client.person.name),
            'contract': lambda d: orm.desc(d.contract.reference),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, Device.SerialNumber))
        return options.get(field_name, Device.SerialNumber)

    @staticmethod
    def by_active_until(device):
        if device.ActiveUntil:
            return device.ActiveUntil

        return datetime(2100, 1, 1, 1, 1, 1, 0)

    @staticmethod
    def by_serial_number(device):
        return device.SerialNumber

    @staticmethod
    def by_owner(device):
        if device.contract and device.contract.client:
            return device.contract.client.person.full_name
        return ' - '

    @staticmethod
    def by_type(device):
        return device.type

    @staticmethod
    def by_offer(device):
        if device.get_offer_code() is not None:
            return '{}'.format(device.get_offer_code())
        return ' - '

    @staticmethod
    def by_mode(device):
        return device.Mode
