from pony import orm
from shared.services.sorter import Sorter

class StockMovementSorter(Sorter):

    @classmethod
    def sort_by(cls, field_name):

        options = {
            'origin_location': cls.by_origin_location,
            'destination_location': cls.by_destination_location
        }

        return options.get(field_name, cls.by_date)

    @classmethod
    def real_field_sort(cls, field_name, desc=False):
        options = {
            'date': lambda move: move.date,
            'serial_number': lambda move: move.stock_item.device.composed_serial,
            'user': lambda move: move.user.person.name + move.user.person.surname,
            'origin_status': lambda move: move.origin_status,
            'origin_location': False,
            'destination_status': lambda move: move.destination_status,
            'destination_location': False,
        }
        options_desc = {
            'date': lambda move: orm.desc(move.date),
            'serial_number': lambda move: orm.desc(move.stock_item.device.composed_serial),
            'user': lambda move: orm.desc(move.user.person.name + move.user.person.surname),
            'origin_status': lambda move: orm.desc(move.origin_status),
            'destination_status': lambda move: orm.desc(move.destination_status),
        }
        default = lambda move: move.date
        if desc:
            return options_desc.get(field_name, options.get(field_name, default))
        return options.get(field_name, default)

    @classmethod
    def by_date(cls, movement):
        return movement.date

    @classmethod
    def by_origin_location(cls, movement):
        if movement.previous:
            if movement.origin_client:
                return movement.origin_client.full_name
            if movement.origin_user:
                return movement.origin_user.full_name
            if movement.origin_shop:
                return movement.origin_shop.name
        return '-'
    
    @classmethod
    def by_destination_location(cls, movement):
        if movement.destination_client:
            return movement.destination_client.full_name
        if movement.destination_user:
            return movement.destination_user.full_name
        if movement.destination_entity:
            return movement.destination_entity.name
        return '-'


class QuantityStockMovementSorter(Sorter):

    @classmethod
    def sort_by(cls, field_name):

        options = {
            'origin_location': cls.by_origin_location,
            'destination_location': cls.by_destination_location
        }

        return options.get(field_name, cls.by_date)

    @classmethod
    def real_field_sort(cls, field_name, desc=False):
        options = {
            'date': lambda move: move.date,
            'quantity': lambda move: move.quantity,
            'user': lambda move: move.user.person.full_name,
            'origin_status': lambda move: move.origin.status,
            'origin_location': False,
            'destination_status': lambda move: move.destination.status,
            'destination_location': False,
        }
        options_desc = {
            'date': lambda move: orm.desc(move.date),
            'quantity': lambda move: orm.desc(move.quantity),
            'user': lambda move: orm.desc(move.user.person.full_name),
            'origin_status': lambda move: orm.desc(move.origin.status),
            'destination_status': lambda move: orm.desc(move.destination.status),
        }
        default = lambda move: move.date
        if desc:
            return options_desc.get(field_name, options.get(field_name, default))
        return options.get(field_name, default)

    @classmethod
    def by_date(cls, movement):
        return movement.date

    @classmethod
    def by_origin_location(cls, movement):
        if movement.origin:
            if movement.origin.user:
                return movement.origin.user.full_name
            if movement.origin.operational_entity:
                return movement.origin.operational_entity.name
        return '-'

    @classmethod
    def by_destination_location(cls, movement):
        if movement.destination:
            if movement.destination.user:
                return movement.destination.user.full_name
            if movement.destination.operational_entity:
                return movement.destination.operational_entity.name
        return '-'
