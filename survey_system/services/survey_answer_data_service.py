from survey_system.models.survey_method import SurveyMethod
from survey_system.services.get_answers_service import SurveyAnswerAnswersGetterService


class SurveyAnswerDataService:

    @classmethod
    def get_survey_answer_data_dict(cls, survey_answer, use_names):
        survey_answer_dict = {
            'id': survey_answer.id,
            'form_id': survey_answer.surveyAnswered.id,
            'start_time': survey_answer.started,
            'end_time': survey_answer.ended,
            'form_method': SurveyMethod.get_name_from_id(survey_answer.surveyMethod),
            'modified_date': survey_answer.modifiedDate,
        }
        if survey_answer.client_answering:
            survey_answer_dict.update({'subject_client_id': survey_answer.client_answering.id})
        if survey_answer.lead_answering:
            survey_answer_dict.update({'subject_lead_id': survey_answer.lead_answering.id})
        if survey_answer.interviewer.user:
            survey_answer_dict.update({'entry_user_id': survey_answer.interviewer.user.id})
        if survey_answer.discussed_topic:
            survey_answer_dict.update({'discussed_topic_id': survey_answer.discussed_topic.id})
        if survey_answer.user_journey_run_step:
            survey_answer_dict.update({'user_journey_run_step_id': survey_answer.user_journey_run_step.id})
        answers = SurveyAnswerAnswersGetterService.get_answers_with_questions(survey_answer, use_names=use_names)
        survey_answer_dict.update({'answers': answers})
        return survey_answer_dict
    

    @classmethod
    def check_if_all_picture_sign_uploaded(cls, surveyAnswer):
        questions = surveyAnswer.getQuestionsInOrder()
        for question in questions:
            if question.getType() == 6 or question.getType() == 13:
                answers = question.getAnswersInSurveyAnswer(surveyAnswer)
                for answer in answers:
                    if not answer.value_stored_file.available:
                        return False
        return True