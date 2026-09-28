from pony import orm
from shared.services.sorter import Sorter

class StockItemSorter(Sorter):

    @classmethod
    def sort_by(cls, field_name):

        options = {
            'location': cls.by_location
        }

        return options.get(field_name, cls.by_serial_number)

    @classmethod
    def real_field_sort(cls, field_name, desc=False):
        options = {
            'serial_number': lambda item: item.device.composed_serial,
            'status': lambda item: item.status,
            'location': False,
        }
        options_desc = {
            'serial_number': lambda item: orm.desc(item.device.composed_serial),
            'status': lambda item: orm.desc(item.status),
        }
        default = lambda item: item.device.composed_serial
        if desc:
            return options_desc.get(field_name, options.get(field_name, default))
        return options.get(field_name, default)

    @classmethod
    def by_serial_number(cls, stock_item):
        return stock_item.device.composed_serial

    @classmethod
    def by_location(cls, stock_item):
        if stock_item.client:
            return stock_item.client.full_name
        if stock_item.user:
            return stock_item.user.full_name
        if stock_item.shop:
            return stock_item.shop.name
        return '-'
