from decimal import Decimal
import dateutil.parser
import pytz
from jsonschema.exceptions import ValidationError


class QueryParametersValidator:

    TRUE_VALUES = ['True', 'true', '1', 'Yes', 'yes']
    FALSE_VALUES = ['False', 'false', '0', 'No', 'no', 'null']

    @classmethod
    def validate_and_decode(cls, args, parameters):
        result = {}
        for param in parameters:
            name = param['name']
            schema = param['schema']
            value = args[name] if name in args else schema.get('default')
            result[name] = cls.decode(value, schema)
        return result

    @classmethod
    def decode(cls, value, schema):
        try:
            type = schema['type']
        except KeyError:
            raise ValidationError('type missing for parameter '+schema['name'])
        format = schema.get('format')
        if type == 'string':
            if format == 'date-time':
                if not value:
                    return None
                return dateutil.parser.parse(value).astimezone(pytz.utc).replace(tzinfo=None)
            return str(value)
        if type == 'number':
            if format == 'integer':
                return int(value)
            if format == 'float':
                return Decimal(value)
        if type == 'boolean':
            if value in cls.TRUE_VALUES:
                return True
            if value in cls.FALSE_VALUES:
                return False
            raise ValueError(f'Invalid boolean value {value} for type {type}')
        if type == 'array':
            return [cls.decode(i, schema['items']) for i in value.split(',')] if value else []
        raise TypeError('Invaid type '+type)
