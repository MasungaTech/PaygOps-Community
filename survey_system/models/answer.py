from datetime import datetime
from pony import orm
from shared.model.cached_model import CachedModelMixin
from survey_system.services.individual_answer_service import AnswerService
from survey_system.models.languages import Languages
from survey_system.models.question import Question
from survey_system.models.answer_group import AnswerGroup
from core_system.core_entities import db


class Answer(db.Entity, CachedModelMixin):
    question = orm.Required(Question, column="question")
    surveyAnswer = orm.Required('SurveyAnswer', column="surveyanswer")
    value_bool = orm.Optional(bool)
    value_text = orm.Optional(str)
    value_numeric = orm.Optional(float)
    value_choice = orm.Optional('QuestionChoice', column="value_choice")
    value_stored_file = orm.Optional('StoredFile', column="value_stored_file")
    value_date = orm.Optional(datetime)
    value_json = orm.Optional(orm.Json)
    time = orm.Optional(datetime)
    orderInSurveyAnswer = orm.Required(int, default=0)
    grouping = orm.Optional(AnswerGroup, column="grouping")

    def set_value(self, value, use_names=False):
        AnswerService.set_answer_value(self, value, use_names)

    def getValue(self, language=None):
        if not language:
            language=Languages.english
        return AnswerService.get_answer_value(self, language)

    def get_answer_value(self, language=None, use_names=False, mobile=False):
        return AnswerService.get_value(answer=self, language=language, use_names=use_names, mobile=mobile)

    def after_insert(self):
        self.surveyAnswer.modifiedDate = datetime.now()
    
    def after_update(self):
        self.surveyAnswer.modifiedDate = datetime.now()


    @property
    def modifiedDate(self):
        return self.surveyAnswer.modifiedDate
