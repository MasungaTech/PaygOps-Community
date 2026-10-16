from datetime import datetime

from flask_restful import Resource, request
from pony import orm

from constants import BOOLEAN_OPTIONAL_OPTIONS_STRING, INTEGER_OPTIONAL_OPTIONS_STRING
from core_system.users.services.current_user_service import get_current_api_user
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from shared.logger.loggers import Error
from survey_system.models.survey_answer import SurveyAnswer
from survey_system.services.survey_answer_getter_service import SurveyAnswerGetterService
from survey_system.services.survey_answer_service import SurveyAnswerService


class AllSurveyAnswersResource(BaseAPIResourceAll):
    ENTITY_REQUIRED = False
    LIST_SERVICE = SurveyAnswerGetterService
    ADD_SERVICE = SurveyAnswerService
    LIST_PERMISSION = ['ViewFormAnswers']
    ADD_PERMISSION = ['EditFormAnswers']
    MODEL = SurveyAnswer
    TAG = 'Custom Forms'
    OBJECT_NAME = 'Form Answers'
    CUSTOM_ORDER = True
    DEFAULT_PAGE_SIZE = 100
    LIST_DESCRIPTION = (
        'List form answers with optional filters. Returns answer IDs by default; '
        'set `include_objects=true` for full answer payloads (same shape as GET '
        '/custom_forms/answers/{id}). Pagination is required when including objects.'
    )

    EXTRA_LIST_PARAMS = {
        'form_id': {
            'in': 'query',
            'name': 'form_id',
            'schema': {'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING},
            'example': '7',
            'allowEmptyValue': True,
            'description': 'Filter by parent form ID (all versions).',
        },
        'form_version_id': {
            'in': 'query',
            'name': 'form_version_id',
            'schema': {'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING},
            'example': '12',
            'allowEmptyValue': True,
            'description': 'Filter by a specific form version ID.',
        },
        'subject_client_id': {
            'in': 'query',
            'name': 'subject_client_id',
            'schema': {'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING},
            'example': '1',
            'allowEmptyValue': True,
            'description': 'Filter by the client who answered the form.',
        },
        'subject_lead_id': {
            'in': 'query',
            'name': 'subject_lead_id',
            'schema': {'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING},
            'example': '2',
            'allowEmptyValue': True,
            'description': 'Filter by the lead who answered the form.',
        },
        'discussed_topic_id': {
            'in': 'query',
            'name': 'discussed_topic_id',
            'schema': {'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING},
            'example': '3',
            'allowEmptyValue': True,
            'description': 'Filter by related discussed topic (enterprise).',
        },
        'answered_by_user_id': {
            'in': 'query',
            'name': 'answered_by_user_id',
            'schema': {'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING},
            'example': '4',
            'allowEmptyValue': True,
            'description': 'Filter by the user (interviewer) who recorded the form.',
        },
        'start_time': {
            'in': 'query',
            'name': 'start_time',
            'schema': {'type': 'string', 'format': 'date-time'},
            'example': datetime(2020, 9, 1, 14, 34, 54).isoformat(),
            'allowEmptyValue': True,
            'description': 'Include answers started at or after this time.',
        },
        'end_time': {
            'in': 'query',
            'name': 'end_time',
            'schema': {'type': 'string', 'format': 'date-time'},
            'example': datetime(2020, 9, 30, 14, 34, 54).isoformat(),
            'allowEmptyValue': True,
            'description': 'Include answers started at or before this time.',
        },
        'date': {
            'in': 'query',
            'name': 'date',
            'schema': {'type': 'string', 'format': 'date-time'},
            'example': datetime(2020, 9, 1).isoformat(),
            'allowEmptyValue': True,
            'description': 'Include answers started on this calendar day.',
        },
        'is_last_answer': {
            'in': 'query',
            'name': 'is_last_answer',
            'schema': {'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING},
            'example': 'true',
            'allowEmptyValue': True,
            'description': 'Filter by whether this is the latest answer for the subject and form.',
        },
        'is_first_answer': {
            'in': 'query',
            'name': 'is_first_answer',
            'schema': {'oneOf': BOOLEAN_OPTIONAL_OPTIONS_STRING},
            'example': 'false',
            'allowEmptyValue': True,
            'description': 'Filter by whether this is the first answer for the subject and form.',
        },
        'includes_question_name': {
            'in': 'query',
            'name': 'includes_question_name',
            'schema': {'type': 'string'},
            'example': 'Reason for late payment',
            'allowEmptyValue': True,
            'description': 'Only answers that include a response to the named question.',
        },
        'includes_question_slug': {
            'in': 'query',
            'name': 'includes_question_slug',
            'schema': {'type': 'string'},
            'example': 'reason-for-late-payment',
            'allowEmptyValue': True,
            'description': 'Only answers that include a response to the question with this slug.',
        },
        'includes_answer_value': {
            'in': 'query',
            'name': 'includes_answer_value',
            'schema': {'type': 'string'},
            'example': 'Other (fill explanation below)',
            'allowEmptyValue': True,
            'description': 'Only answers with a text response matching this value (v1: text answers).',
        },
        'includes_question_type': {
            'in': 'query',
            'name': 'includes_question_type',
            'schema': {'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING},
            'example': '1',
            'allowEmptyValue': True,
            'description': 'Only answers that include a response to a question of this type.',
        },
        'slug_as_keys': {
            'in': 'query',
            'name': 'slug_as_keys',
            'schema': {
                'type': 'string',
                'enum': ['true', 'false', 'True', 'False'],
            },
            'example': 'true',
            'required': False,
            'allowEmptyValue': True,
            'description': (
                'When `include_objects=true`, return answers keyed by question slug '
                '(same as individual GET).'
            ),
        },
    }


class AllSurveyAnswersResourceOld(Resource):

    @verify(permissions='EditFormAnswers', validate_json=True)
    @orm.db_session
    def post(self):
        skip_hook = request.json.get('skip_hook', False) in [True, 'true']
        use_names = not (request.json.get('use_ids', False) in [True, 'true'])
        try:
            data = request.json
            if skip_hook:
                data['skip_hook'] = skip_hook
            this_answer = SurveyAnswerService.add_from_data_and_user(
                data, get_current_api_user(), use_names=use_names)
        except Error as error:
            orm.rollback()
            raise error
        else:
            orm.commit()
            with orm.db_session:
                this_survey_answer_dict = SurveyAnswerService.get_survey_answer_data_dict(
                    this_answer, use_names=use_names)
                return this_survey_answer_dict, 201
