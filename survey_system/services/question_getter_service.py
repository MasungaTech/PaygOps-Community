from shared.services.base_getter_service import BaseGetterService
from survey_system.models.question import Question
from survey_system.models.question_choice import QuestionChoice


class QuestionGetterService(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        return Question.select()


class QuestionChoiceGetterService(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        return QuestionChoice.select()