from pony import orm
from decimal import Decimal


class BaseAnalyticalDBModel:

    _description_ = ''

    @classmethod
    def selector(cls, objects):
        return orm.select(obj for obj in objects).order_by(lambda obj: cls.extended_modified_date(obj))

    @staticmethod
    def extended_modified_date(obj):
        return obj.modifiedDate

    @staticmethod
    def get_set_converter():
        return None

    @staticmethod
    def bulk_allowed():
        return True # Always allowed unless there is a good reason

    @staticmethod
    def default_page_size_cat():
        return None

    @staticmethod
    def _convert_decimal_to_float_dict(dict_object):
        return {k:float(v) if isinstance(v, Decimal) else v for k, v in dict_object.items()}
