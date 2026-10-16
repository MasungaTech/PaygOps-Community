from functools import partial

import factory
from datetime import datetime
from payg_loan_system.devices.model.device import Device
from payg_loan_system.offers.tests.factories import TimeOfferFactory
from munch import DefaultMunch


class DeviceFactory(factory.Factory):
    class Meta:
        model = Device

    SerialNumber = factory.Sequence(lambda n: n)
    serial_number = factory.Sequence(lambda n: n)
    composed_serial = 'SOL-'+str(SerialNumber)
    type = 'SOL'
    RegistrationTime = datetime.today()
    ActiveUntil = datetime.today()
    Mode = 1
    offer = TimeOfferFactory.stub()
    contract = 'GENERATE'
    stock_item = DefaultMunch({})
    credit_balance = None
    credit_unit = None
    allowed_units = {}
    allocated_lead = None

    @classmethod
    def stub(cls, *args, **kwargs):
        device = super().stub(*args, **kwargs)
        if device.contract == 'GENERATE':
            from payg_loan_system.contracts.services.tests.factories import ContractFactory
            device.contract = ContractFactory.stub(linked_device=device)
        device.get_remaining_activation_time_in_hours = partial(Device.get_remaining_activation_time_in_hours, device)
        device.clear = partial(Device.clear, device)
        device.get_offer = partial(Device.get_offer, device)
        device.get_display_name = partial(Device.get_display_name, device)
        device.can_use_offer = partial(Device.can_use_offer, device)
        device.get_mode_name = partial(Device.get_mode_name, device)
        device.is_compatible_with_offer = partial(Device.is_compatible_with_offer, device)
        device.is_nonpayg = partial(Device.is_nonpayg, device)
        device.get_api_data = partial(Device.get_api_data, device)
        return device


class DeviceAbstractFactory:
    @staticmethod
    def create():
        return DeviceFactory.stub()

    @staticmethod
    def create_no_client():
        device = DeviceFactory.stub()
        device.contract = None
        return device
