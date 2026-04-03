from shared.helpers.pagination import ResultSet
from pony import orm
from shared.logger.loggers import LogAPI
logger = LogAPI()


class Sorter:

    @classmethod
    def sort(cls, resultset, string, field_name="name", order="asc"):

        try:
            if string:
                split = string.split(':')
                if len(split) > 1:
                    field_name, order = string.split(":")
        except ValueError as e:
            LogAPI.Fatal(e)
            print("Error {}".format(e))

        try:
            if cls.real_field_sort(field_name):
                if order.lower() == 'desc':
                    sorted_results = resultset.without_distinct().order_by(orm.desc(cls.real_field_sort(field_name, desc=True)))
                else:
                    sorted_results = resultset.without_distinct().order_by(cls.real_field_sort(field_name))
                return sorted_results
        except Exception as error:
            logger.Fatal(error)

        resultset = sorted(resultset, key=cls.sort_by(field_name))
        
        return cls._set_order(resultset, order=order)
    
    @staticmethod
    def sort_by(field_name):
        pass

    @staticmethod
    def _set_order(sorted_resultset, order='asc'):
        if order.lower() == 'desc':
            sorted_resultset = sorted_resultset[::-1]

        return ResultSet(sorted_resultset)

    @staticmethod
    def by_id(object):
        return object.id

    @staticmethod
    def real_field_sort(field_name, desc=False):
        return False
