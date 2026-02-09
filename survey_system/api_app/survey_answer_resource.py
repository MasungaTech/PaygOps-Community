from flask_restful import Resource, request
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from pony import orm
from shared.logger.loggers import LogService
from core_system.users.services.current_user_service import get_current_api_user
from shared.logger.loggers import Error
from survey_system.services.survey_answer_service import SurveyAnswerService, SurveyAnswer
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll


class AllSurveyAnswersResource(BaseAPIResourceAll):
    ENTITY_REQUIRED = False
    LIST_SERVICE = None
    ADD_SERVICE = SurveyAnswerService
    LIST_PERMISSION = []
    ADD_PERMISSION = ['EditFormAnswers']
    MODEL = SurveyAnswer
    TAG = 'Custom Forms'
    OBJECT_NAME = 'Form Answers'


class AllSurveyAnswersResourceOld(Resource):

    @verify(permissions='EditFormAnswers', validate_json=True)
    @orm.db_session
    def post(self):
        skip_hook = request.json.get('skip_hook', False) in [True, 'true']
        use_names=not (request.json.get('use_ids', False) in [True, 'true'])
        try:
            data = request.json
            if skip_hook:
                data['skip_hook'] = skip_hook
            this_answer = SurveyAnswerService.add_from_data_and_user(data, get_current_api_user(), use_names=use_names)
        except Error as error:
            orm.rollback()
            raise error
        else:
            orm.commit()
            with orm.db_session:
                this_survey_answer_dict = SurveyAnswerService.get_survey_answer_data_dict(this_answer, use_names=use_names)
                return this_survey_answer_dict, 201