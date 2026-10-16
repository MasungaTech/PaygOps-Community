from pony.orm import db_session
from flask import abort


class ModelInterface:
    @classmethod
    @db_session
    def all(cls):
        return cls.select()

    @classmethod
    @db_session
    def first(cls):
        return cls.all().first()

    @classmethod
    @db_session
    def get_or_404(cls, id):
        object = cls.get(id=id)
        if object:
            return object

        abort(404)
