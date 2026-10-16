from pony import orm

from core_system.core_entities import db
from survey_system.models.languages import Languages
from shared.helpers import db_helpers


class QuestionChoiceText(db.Entity):
    questionChoice = orm.Required('QuestionChoice', column="questionchoice")
    language = orm.Required(int, index=True)
    value_text = orm.Optional(str)

    def before_insert(self):
        if not Languages.valid(self.language):
            raise ValueError
