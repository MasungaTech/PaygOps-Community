from decimal import Decimal
from json import JSONEncoder


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return JSONEncoder.default(self, obj)


def default_function(obj):  
    if isinstance(obj, Decimal):
        return float(obj)