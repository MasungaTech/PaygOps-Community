from pony import orm

from core_system.core_entities import db
from survey_system.models.question_choice_text import QuestionChoiceText


class QuestionChoice(db.Entity):
    text = orm.Set('QuestionChoiceText')
    value_numeric = orm.Optional(float)
    question = orm.Required('Question', column="question")
    order = orm.Optional(int)
    answerWithChoice = orm.Set('Answer', cascade_delete=True)

    def getText(self, language):
        return orm.select(CT for CT in QuestionChoiceText if CT.questionChoice == self and CT.language == language)\
            .first().value_text

    def getValue(self):
        if self.question.isInt:
            return int(self.value_numeric)
        else:
            return self.value_numeric

    @property
    def display_value(self):
        return self.getValue() if self.question.is_numeric_type() else self.getText(1)

    # def before_insert(self):
    #     if (orm.count(self.text) == 0) and self.value_numeric == None:
    #         raise ValueError

