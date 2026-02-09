from pony import orm
from stock_management_system.models import StockItem
from shared.services.base_service import BaseService


class DeviceDeleteService(BaseService):

    @classmethod
    def _delete_from_object_and_user(cls, device, user=None):
        if device.stock_item.reserved:
            raise Error(
                '''You cannot edit a device that has a pending movement,
                please approve or reject the movement before deleting'''
            , 'DEVICE_RESERVED')
        if device.contract is not None:
            raise Exception('CANNOT_DELETE_DEVICE_WITH_CLIENT')
        if device.ActiveUntil is not None:
            raise Exception('CANNOT_DELETE_DEVICE_WITH_TIME')
        if orm.count(device.ActivationRequests) != 0:
            raise Exception('CANNOT_DELETE_DEVICE_USED')
        if orm.count(device.MentorRequests) != 0:
            raise Exception('CANNOT_DELETE_DEVICE_USED')
        if orm.count(device.transaction_requests) != 0:
            raise Exception('CANNOT_DELETE_DEVICE_USED')
        stock_item = device.stock_item
        device.delete()
        for move in stock_item.movements:
            move.delete()
        sid = stock_item.id
        orm.commit()
        StockItem[sid].delete()
