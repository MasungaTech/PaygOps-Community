from decimal import Decimal
from flask import Flask, jsonify
from json import JSONEncoder
import datetime


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime.datetime):
                pythonISODateStr = obj.isoformat()
                javascriptISODateStr = pythonISODateStr.replace('+00:00', '')
                if not javascriptISODateStr.endswith('Z'):
                    javascriptISODateStr += 'Z'
                return javascriptISODateStr
            elif isinstance(obj, Decimal):
                return float(obj)
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)
