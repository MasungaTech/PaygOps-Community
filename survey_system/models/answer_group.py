from pony import orm
from core_system.core_entities import db


class AnswerGroup(db.Entity):
    answers = orm.Set('Answer')
