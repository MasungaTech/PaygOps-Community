from flask_login import current_user, login_required
from flask import flash, redirect, url_for
from pony.orm import db_session
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from shared.helpers.authorizer import authorizer
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.services.device_delete_service import DeviceDeleteService
from . import device_views


@device_views.route('/<int:device_id>/delete', methods=['GET', 'POST'])
@login_required
@authorizer('DeleteDevices')
@db_session
def delete_device(device_id):
    this_device = DeviceGetterService.get_from_user_and_id(current_user, id=device_id, strict=True, main_resource=True)
    try:
        DeviceDeleteService.delete_from_object_and_user(this_device, current_user)
        flash('Device deleted successfully. ')
        return redirect(url_for('stock.stock_list'))
    except Exception as error:
        flash('Device cannot be deleted, it has data attached to it. ')
        return redirect(url_for('device.view_device', device_id=device_id))

