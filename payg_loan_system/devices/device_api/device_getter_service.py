from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.devices.model.device import Device
from pony import orm
from shared.services.settings_service import SettingsService
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIRequestService, DeviceAPIError
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.non_payg_device_service import NonPAYGDeviceService
from constants import NON_PAYG_TYPE, NON_PAYG_IDENTIFIER


class DeviceGetterService(BaseGetterService):

    OBJ_NAME = 'Device'

    @classmethod
    def get_from_filtered_view(cls, user, view=None, entity=None, search=None):

        extra = {}
        if view == 'managed_by_me':
            extra = dict(managed_by=user)
        elif view == 'orphaned':
            extra = dict(orphaned=True)

        devices = cls.get_list(user, search=search, entity=entity, **extra)

        return devices

    @classmethod
    def get_filtered_objects(cls, current_user, serial_number=None, client=None, search=None, orphaned=None, managed_by=None, available=None, entity=None, serial_number_without_prefix=None, exact_serial_number=None, **kwargs):
        from stock_management_system.services.stock_item_getter_service import StockItemGetterService
        devices = orm.select(device for device in Device)
        is_filtered = False
        if serial_number:
            is_filtered = True
            devices = devices.filter(lambda d: serial_number.lower() in d.composed_serial.lower())
        if serial_number_without_prefix or exact_serial_number:
            serial_number = serial_number_without_prefix if serial_number_without_prefix else exact_serial_number
            is_filtered = True
            devices = devices.filter(lambda d: d.SerialNumber == serial_number)

        if client:
            is_filtered = True
            devices = devices.filter(lambda d: d.contract.client == client)
        if search:
            is_filtered = True
            devices = devices.filter(lambda d: search.lower() in d.composed_serial.lower())
        if orphaned is not None:
            devices = devices.filter(lambda d: bool(d.contract) != orphaned)
        if available:
            devices = devices.filter(lambda d: d.contract is None and d.addon is None and d.allocated_lead is None and not d.stock_item.reserved)
        if is_filtered:
            # This is an optimization to avoid checking all of the  devices
            device_count = devices.count()
            if device_count == 0:
                return devices
            elif device_count == 1:
                this_device = devices.first()
                if StockItemGetterService.user_can_see(this_device.stock_item, current_user):
                    return devices
                else:
                    return devices.filter(lambda d: d.id == -1) # The user cannot see the device
        if not entity and current_user.can_access_in_all('InStockViewStock') \
            and current_user.can_access_in_all('WithUsersViewStock') \
            and current_user.can_access_in_all('WithClientsViewStock') \
            and current_user.can_access('OrphanedViewStock'):
            return devices
        else:
            # The stock item getter is quite slow, so better to avoid using it
            stock_items = StockItemGetterService.get_list(current_user, managed_by=managed_by, entity=entity)
            devices = devices.filter(lambda device: device.stock_item in stock_items)
            return devices

    @classmethod
    def get_device_from_registration_code(cls, registration_code):
        if registration_code == NON_PAYG_IDENTIFIER:
            return NonPAYGDeviceService.create_non_payg_device()
        code, device_type = DeviceAPIService.get_code_and_type_from_composed_code(registration_code)
        this_device = cls._get_device_from_registration_code_and_type(code, device_type)
        return this_device

    @classmethod
    def get_device_from_client_and_activation_code_optional(cls, this_client, activation_request_code=None):
        if not activation_request_code:
            return cls._get_device_from_client_only(this_client)
        else:
            return cls._get_device_from_client_and_activation_code(this_client, activation_request_code)

    @classmethod
    def get_device_from_serial_number_only(cls, serial_number, sensitive=True, raise_if_absent=True):
        serial, device_type = DeviceAPIService.get_code_and_type_from_composed_code(serial_number)
        this_device = cls._get_device_from_serial_number_and_type(serial, device_type, sensitive=sensitive, raise_if_absent=raise_if_absent)
        return this_device

    @classmethod
    def _get_device_from_client_and_activation_code(cls, this_client, activation_request_code):
        code, device_type = DeviceAPIService.get_code_and_type_from_composed_code(activation_request_code)
        this_device = cls._get_device_from_activation_code_and_type_and_client_optional(
            code,
            device_type,
            this_client
        )
        return this_device

    @classmethod
    def _get_device_from_activation_code_and_type_and_client_optional(cls, activation_code, device_type, this_client=None):
        if device_type == NON_PAYG_TYPE:
            return cls._get_device_from_serial_number_and_type(activation_code, device_type)
        api_type = cls._get_api_type_from_device_type(device_type)
        if api_type == "TWO_WAY_CODE":
            if this_client:
                devices = orm.select(D for D in Device if D.contract.client == this_client and
                                     D.type == device_type and D.contract.status == ContractStatus.active)
                if devices.count() == 1:
                    return devices.first()
            # We cannot support multiple TWO_WAY_CODE devices
            raise DeviceAPIError('CLIENT_HAS_SEVERAL_DEVICE')
        else:
            this_device = cls._get_device_from_serial_number_and_type(activation_code, device_type)
        return this_device

    @classmethod
    def _get_device_from_registration_code_and_type(cls, code, device_type):
        if device_type == NON_PAYG_TYPE:
            return cls._get_device_from_serial_number_and_type(code, device_type)
        api_type = cls._get_api_type_from_device_type(device_type)
        if api_type == "TWO_WAY_CODE":
            handler = DeviceAPIRequestService.get_device_api_helper(device_type)
            this_device_serial = handler.get_device_from_code(code)
            this_device = cls._get_device_from_serial_number_and_type(this_device_serial, device_type)
        else:
            this_device = cls._get_device_from_serial_number_and_type(code, device_type)
        return this_device

    @classmethod
    def _get_api_type_from_device_type(cls, device_type):
        devices_api = SettingsService.get_setting('AllDeviceAPIS')
        this_device_api = devices_api.get(device_type)
        this_device_api_type = this_device_api.get('device_api_type')
        return this_device_api_type

    @classmethod
    def _get_device_from_serial_number_and_type(cls, serial_number, device_type, sensitive=True, raise_if_absent=True):
        if sensitive:
            this_device = orm.select(device for device in Device
                                 if device.SerialNumber == serial_number
                                 and device.type == device_type).first()
        else:
            this_device = orm.select(device for device in Device
                                 if device.SerialNumber.lower() == serial_number.lower()
                                 and device.type == device_type).first()
        if this_device is not None:
            return this_device
        if raise_if_absent:
            raise DeviceAPIError('DEVICE_NOT_PREREGISTERED')

    @classmethod
    def _get_device_from_client_only(cls, this_client):
        devices = orm.select(D for D in Device if D.contract.client == this_client and D.contract.status == ContractStatus.active)
        if devices.count() > 1:
            raise DeviceAPIError('CLIENT_HAS_SEVERAL_DEVICE')
        if devices.count() == 0:
            raise DeviceAPIError('CLIENT_HAS_NO_DEVICE')
        return devices.first()
    
    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids, **kwargs):
        if 'lead' not in cached_ids:
            leads = LeadGetterService.get_list_for_mobile(current_user)
            cached_ids['lead'] = orm.select(l.id for l in leads)[:]
        if 'contract' not in cached_ids:
            relevant_clients_ids = cached_ids['client']
            contracts = current_user.get_relevant_contracts_for_mobile(relevant_clients_ids)
            cached_ids['contract'] = orm.select(e.id for e in contracts)[:]
        return current_user.get_devices_for_mobile(cached_ids['contract'], cached_ids['lead'])
