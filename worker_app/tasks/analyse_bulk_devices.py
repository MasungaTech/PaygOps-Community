from payg_loan_system.devices.model.product_sub_type import ProductSubType
from shared.services.background_task_base import BackgroundTask
from pony import orm
from worker_app.worker_app import worker_app
from payg_loan_system.devices.model.device import Device
from constants import NON_PAYG_TYPE


@worker_app.task
@orm.db_session
def analyse_bulk_devices(task_uuid):

    print('Analysing bulk devices...')

    task_service = BackgroundTask(task_uuid)

    lines = task_service.read_csv_file()
    data, errors = [], {}

    total_devices, correct_devices = 0, 0
    for line in lines:
        if [l.lower() for l in line] == ['serial number', 'sub-type']:
            continue
        total_devices += 1
        if len(line) != 2:
            errors[total_devices] = f'Line with incorrect format.'
            continue
        device = line[0].strip()
        subtype = line[1].strip()
        if len(device) > 24:
            errors[total_devices] = f'Device "{device}" has a Serial Number with more than 20 characters.'
            continue
        if device in data:
            errors[total_devices] = f'Device "{device}"" is being added twice.'
            continue
        if Device.select(lambda d: d.SerialNumber.lower() == device.lower() and d.type == NON_PAYG_TYPE).first():
            errors[total_devices] = f'Device "{device}" is already in the platform.'
            continue
        if subtype:
            pst = ProductSubType.get(lambda pst: pst.name == subtype)
            if not pst:
                errors[total_devices] = f'Product sub-type "{subtype}" is not set up in the platform.'
                continue
            if not pst.device_type == 'NPG':
                errors[total_devices] = f'Product sub-type "{subtype}" is not set up for NPG device type.'
                continue
        correct_devices += 1
        data.append([device, subtype])

    task_service.complete_analysis({
        'correct_devices': correct_devices,
        'total_devices': total_devices,
        'errors': errors
    }, data)
