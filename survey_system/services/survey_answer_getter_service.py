from shared.services.base_getter_service import BaseGetterService
from survey_system.models.survey_answer import SurveyAnswer


class SurveyAnswerGetterService(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        return SurveyAnswer.select()
    
    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids, **kwargs):
        return current_user.get_relevant_survey_answers_for_mobile(cached_ids)
    

    @classmethod
    def get_all_versions_of_answer(cls, form_answer_id):
        """
        Returns all versions of a given survey answer (from the same person)
        """
        answer = SurveyAnswer.get(id=form_answer_id)
        if not answer:
            return []
        form_id = answer.surveyAnswered.form.id
        person = answer.person_answering
        return SurveyAnswer.select().filter(lambda sa: sa.surveyAnswered.form.id == form_id and sa.personAnswering == person)