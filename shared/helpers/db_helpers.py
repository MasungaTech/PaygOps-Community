import math
from pony.orm import Optional as BaseOptional, Required as BaseRequired, PrimaryKey as BasePrimaryKey
import config
import unicodedata

from shared.logger.loggers import Error


class ExtendedAtrributeMixin:

    def __init__(attr, py_type, comment='', csv_columns=None, precision=None, force_time=None, *args, **kwargs):
        attr.comment = comment
        attr.csv_columns = csv_columns
        attr.precision = precision
        attr.force_time = force_time
        super().__init__(py_type, *args, **kwargs)

class Optional(ExtendedAtrributeMixin, BaseOptional): # Order is important here
    pass

class Required(ExtendedAtrributeMixin, BaseRequired): # Order is important here
    pass

class PrimaryKey(ExtendedAtrributeMixin, BasePrimaryKey): # Order is important here
    pass


def set_transaction_readonly(db):
    if config.ENV_VAR == 'TEST':
        return # This does not work in SQLite
    db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")


def set_force_indexes(db):
    if config.ENV_VAR == 'TEST':
        return # This does not work in SQLite
    db.execute("SET LOCAL enable_seqscan = off")


def getMemberVariables(obj):
    return [vars(obj)[attr] for attr in vars(obj) if not callable(getattr(obj(), attr)) and not attr.startswith("__")]


def searchable_text(raw_text):
    # We make the text lower
    lower_text = raw_text.lower()
    # We now remove the accents
    nfkd_form = unicodedata.normalize('NFKD', lower_text)
    return u''.join([c for c in nfkd_form if not unicodedata.combining(c)])


def get_float_columns(entity):
    float_columns = []
    for attr in entity._attrs_:
        if attr.py_type is float:
            float_columns.append(attr.name)
    return float_columns



class TypeClassBase:

    _human_codes = {}

    @classmethod
    def __class_getitem__(cls, key):
        return cls.to_dict()[key]

    @classmethod
    def valid(cls, value, flex_type=False):
        for attr in cls.__dict__:
            if attr[:1] != '_':
                if getattr(cls, attr) == value or (flex_type and str(getattr(cls, attr)) == str(value)):
                    return True
        return False

    @classmethod
    def ovalid(cls, value):
        if not value:
            return True
        for attr in cls.__dict__:
            if attr[:1] != '_' and getattr(cls, attr) == value:
                return True
        return False

    @classmethod
    def ovalidate(cls, value):
        if not value:
            return
        for attr in cls.__dict__:
            if attr[:1] != '_' and getattr(cls, attr) == value:
                return value
        raise Error('Value {value} is not valid', value=value)

    @classmethod
    def valid_code(cls, attr):
        return attr in cls.__dict__

    @classmethod
    def to_dict(cls):
        dicted = {}
        for attr in cls.__dict__:
            if attr[:1] != '_':
                dicted[attr] = getattr(cls, attr)
        return dicted

    @classmethod
    def keys(cls):
        return [k for k in cls.__dict__ if k[:1] != '_']

    @classmethod
    def to_inv_dict(cls):
        dicted = {}
        for attr in cls.__dict__:
            if attr[:1] != '_':
                dicted[getattr(cls, attr)] = attr
        return dicted

    @classmethod
    def to_list(cls):
        listed = []
        for attr in cls.__dict__:
            if attr[:1] != '_':
                listed.append(getattr(cls, attr))
        return listed

    @classmethod
    def to_human(cls, val):
        return cls._human_codes.get(val) or val
    
    @classmethod
    def to_human_dict(cls):
        return {k: cls.to_human(k) for k in cls.to_list()}
    
    @classmethod
    def get_from_human(cls, human):
        for k, v in cls._human_codes.items():
            if human == v:
                return k
        raise ValueError(f'{human} is not a valid {cls.__name__}, possible values are: {list(cls.to_human_dict().values())}')

    @classmethod
    def get_property_name_from_id(cls, id):
        mapping = {v: k for k, v in vars(cls).items() if not k.startswith('__') and isinstance(v, int)}
        return mapping[id]

