from flask_restful import Resource, request
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from pony import orm
from shared.logger.loggers import LogAPI
from core_system.users.services.current_user_service import get_current_api_user
from shared.logger.loggers import Error
from survey_system.services.survey_answer_getter_service import SurveyAnswerGetterService
from survey_system.services.survey_answer_service import SurveyAnswerService, SurveyAnswer
from survey_system.services.error_message_service import SurveyAnswerErrorMessageService
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual

log_api = LogAPI()


class IndividualSurveyAnswersResource(BaseAPIResourceIndividual):
    GET_SERVICE = SurveyAnswerGetterService
    GET_PERMISSION = 'ViewFormAnswers'
    EDIT_SERVICE = SurveyAnswerService
    EDIT_PERMISSION = 'EditFormAnswers'

    MODEL = SurveyAnswer
    TAG = 'Custom Forms'
    OBJECT_NAME = 'Form Answers'

    @classmethod
    def _get_relevant_entity(cls, this_object):
        if this_object.client_answering:
            return this_object.client_answering.person.village
        elif this_object.lead_answering:
            return this_object.lead_answering.person.village
        elif this_object.discussed_topic:
            return this_object.discussed_topic.interaction.client.person.village


class IndividualSurveyAnswersResourceOld(Resource):

    @verify(permissions='ViewFormAnswers')
    @orm.db_session
    def get(self, survey_answer_id):
        survey_answer = SurveyAnswerGetterService.get_from_user_and_id(get_current_api_user(), survey_answer_id, strict=True, main_resource=True)
        this_survey_answer_dict = SurveyAnswerService.get_survey_answer_data_dict(survey_answer, use_names=True)
        return this_survey_answer_dict, 200

    @verify(permissions='EditFormAnswers', validate_json=True)
    @orm.db_session
    def post(self, survey_answer_id):
        skip_hook = request.args.get('skip_hook', False) in [True, 'true']
        use_names=not (request.json.get('use_ids', False) in [True, 'true'])
        survey_answer = SurveyAnswerGetterService.get_from_user_and_id(get_current_api_user(), survey_answer_id, strict=True, main_resource=True)
        try:
            data = request.json
            if skip_hook:
                data['skip_hook'] = skip_hook
            this_answer = SurveyAnswerService.edit_from_data_and_user(survey_answer, data, get_current_api_user(), use_names=use_names)
        except Error as error:
            orm.rollback()
            raise error
        else:
            orm.commit()
            with orm.db_session:
                this_survey_answer_dict = SurveyAnswerService.get_survey_answer_data_dict(this_answer, use_names=use_names)
                return this_survey_answer_dict,  200
