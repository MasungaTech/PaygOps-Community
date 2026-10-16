from pony import orm

from core_system.core_entities import db

class QuestionGroup(db.Entity):
    questions = orm.Set('OrderedQuestion')

    def getSubQuestions(self):
        return self.questions.order_by(db.OrderedQuestion.order).filter(lambda OQ: OQ.isSubQuestion)
