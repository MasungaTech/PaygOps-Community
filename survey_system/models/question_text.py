from pony import orm

from core_system.core_entities import db
from survey_system.models.languages import Languages
from shared.helpers import db_helpers


class QuestionText(db.Entity):
    language = orm.Required(int, index=True)
    fullQuestion = orm.Optional(str)
    variableName = orm.Required(str)
    question = orm.Required('Question', column="question")
    orm.composite_key(language, question)

    def before_insert(self):
        if not Languages.valid(self.language):
            raise ValueError(f'This question "{self.fullQuestion}" has a non valid language {self.language}')
