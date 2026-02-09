from core_system.users.services.user_getter_service import UserGetterService
from shared.services.background_task_base import BackgroundTask
from shared.services.settings_service import SettingsService
from stock_management_system.services.permission_helpers import StockMovementPermissionHelper
from core_system.core_entities import db
from core_system.users.models.user_model import User
from stock_management_system.stock_status import StockStatus
from payg_loan_system.devices.device_api.device_api_errors import DeviceAPIError
from shared.logger.loggers import Error
from pony import orm
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from worker_app.worker_app import worker_app

HEADER = ['serial number', 'destination', 'note', 'hub id', 'user id']


@worker_app.task
@orm.db_session
def analyse_bulk_stock_movements(uuid):
    operational_entities_config = SettingsService.get_setting('OperationalEntities')
    shop_name = operational_entities_config[2]['name']

    print('Analysing bulk stock movements...')
    task_service = BackgroundTask(uuid)
    acting_user = User.get(id=task_service.user)
    phones_file = task_service.read_csv_file()

    correct_movements = 0
    status_counts = {
        'in_stock': 0,
        'with_user': 0,
        'orphaned': 0,
        'lost': 0
    }
    correct_movements = 0
    total_movements = 0
    data = []
    errors = {}
    fallback = SettingsService.get_setting('FallBackDeviceType')

    for line in phones_file:
        if total_movements == 0 and [h.lower().strip() for h in line] == HEADER:
            continue
        total_movements += 1
        if not(2 <= len(line) <= 5):
            errors[total_movements] = f'Incorrect format, the row must have 2 to 5 columns.'
            continue
        device_serial = line[0].lower().strip()
        if device_serial.count('-') > 1:
            errors[total_movements] = f'Device Serial Number format incorrect "{line[0]}" (only one "-" allowed, separating device type and serial number)'
            continue
        if device_serial.count('-') == 0 and fallback == 'DISABLED':
            errors[total_movements] = f'Missing device type for device "{line[0]}". Example: "NPG-{line[0]}"'
            continue
        try:
            device = DeviceGetterService.get_device_from_serial_number_only(device_serial, sensitive=False)
        except (DeviceAPIError, Error) as error:
            if fallback == 'DISABLED':
                errors[total_movements] = f'Device Serial Number not found "{line[0]}"'
                continue
            errors[total_movements] = f'Device Serial Number not found "{fallback}-{line[0]}"'
            continue
        if device.stock_item.status == StockStatus.installed:
            errors[total_movements] = f'It is not possible to manually move an installed device.'
            continue
        if device.stock_item.id in [m[0] for m in data]:
            errors[total_movements] = f'Item "{line[0]}" has already been used in a previous movement.'
            continue
        status = line[1].lower().strip().replace(' ', '_')
        if not StockStatus.valid(status) or status == StockStatus.installed:
            errors[total_movements] = f'Invalid Destination "{line[1]}"'
            continue
        note = line[2] if len(line) > 2 else ''
        hub_id = line[3].strip() if len(line) > 3 else ''
        hub = None
        if status == StockStatus.in_stock:
            try:
                # Updated to OperationalEntity to fix the error
                hub = db.OperationalEntity.get(id=hub_id)
                if not hub:
                    errors[total_movements] = f'{shop_name} not found with Id "{hub_id}"'
                    continue
            except (ValueError, TypeError):
                errors[total_movements] = f'Invalid {shop_name} Id value "{hub_id}"'
                continue
        elif hub_id != '':
            errors[total_movements] = f'{shop_name} Id provided "{hub_id}", but Destination is not in_stock.'
            continue
        user_id = line[4].strip() if len(line) > 4 else ''
        user = None
        if status == StockStatus.with_user:
            try:
                user = UserGetterService.get_from_user_and_id(acting_user, user_id)
                if not user:
                    errors[total_movements] = f'User not found with Id "{user_id}"'
                    continue
            except (ValueError, TypeError):
                errors[total_movements] = f'Invalid User Id value "{user_id}"'
                continue
        elif user_id != '':
            errors[total_movements] = f'User Id provided "{user_id}", but Destination is not with_user.'
            continue
        if not StockMovementPermissionHelper.user_can_move(device.stock_item, {
            'status': status,
            'user': user,
            'shop': hub
        }, acting_user):
            errors[total_movements] = f'You do not have enough permissions to make this movement.'
            continue
        if device.stock_item.status == status and device.stock_item.user == user and device.stock_item.shop == hub:
            errors[total_movements] = f'The stock item is already in this place.'
            continue
        correct_movements += 1
        status_counts[status] += 1
        data.append([device.stock_item.id, status, note, getattr(user, 'id', None), getattr(hub, 'id', None)])
    task_service.complete_analysis({
        'correct_movements': correct_movements,
        'total_movements': total_movements,
        'status_counts': status_counts,
        'errors': errors
    }, data)
