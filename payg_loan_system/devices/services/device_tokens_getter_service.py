from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.device_api.device_api_errors import DeviceAPIError
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService
from pony.orm import desc
from shared.helpers.form_helpers import value_to_bool


class DeviceTokensGetterService(BaseGetterService):

    OBJ_NAME = 'Token'

    @classmethod
    def get_filtered_objects(cls, current_user, serial_number, reverse_order=False, **kwargs):
        all_devices = DeviceGetterService.get_list(current_user)
        try:
            device = DeviceGetterService.get_device_from_serial_number_only(serial_number)
        except DeviceAPIError as error:
            raise Error(str(error))
        allowed = all_devices.filter(lambda d: d.composed_serial == device.composed_serial)
        if allowed.count() == 0:
            return None
        if value_to_bool(reverse_order):
            return device.tokens.order_by(lambda t: desc(t.time))
        return device.tokens.order_by(lambda t: t.time)
