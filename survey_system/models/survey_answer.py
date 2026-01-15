from datetime import datetime
from survey_system.models.survey_method import SurveyMethod
from pony import orm
from core_system.core_entities import db
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from shared.model.cached_model import CachedModelMixin
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from constants import INTEGER_OPTIONAL_OPTIONS, BOOLEAN_OPTIONAL_OPTIONS
from survey_system.services.get_answers_service import SurveyAnswerAnswersGetterService
from shared.logger.loggers import Error
from shared.helpers.form_helpers import value_to_bool
import config



class SurveyAnswer(db.Entity, ModelDefinitionMixin, CachedModelMixin):
    surveyAnswered = orm.Required('FormVersion', column="surveyanswered")
    modifiedDate = orm.Required(datetime, default=datetime.now, index=True, volatile=True)
    lead_answering = orm.Optional('Lead', column="lead_answering") # if it has lead (with or without client), it was created at lead stage
    client_answering = orm.Optional('Client', column="client_answering") # if it has ONLY client, it was created at client stage.
    surveyMethod = orm.Required(int)

    interviewer = orm.Optional('Person', column="interviewer")
    started = orm.Optional(datetime, index=True)
    ended = orm.Optional(datetime)

    # Enterprise-only relations: when enterprise features are disabled, keep the
    # underlying FK columns as plain integers so Pony doesn't require the
    # corresponding entities to exist.
    if getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False):
        discussed_topic = orm.Optional('DiscussedTopic')
        user_journey_run_step = orm.Optional('UserJourneyRunStep')
    else:
        discussed_topic = orm.Optional(int)
        user_journey_run_step = orm.Optional(int)

    is_last_answer = orm.Required(bool, default=False, index=True)
    is_first_answer = orm.Required(bool, default=False, index=True)

    answers = orm.Set('Answer')
    mobile_uuid = orm.Optional(str)

    personAnswering = orm.Optional('Person', column="personanswering") # This is not the source of truth, but it is correct

    # Cached data
    cached_data = orm.Optional(orm.Json, volatile=True)

    PARAMETERS = [
        {
            'in': 'query',
            'name': 'slug_as_keys',
            'schema': {
                "type": "string",
                "enum": ['true', 'false', 'True', 'False']
            },
            "required": False,
            "examples": {
                'true': {
                    "value": "true",
                    "summary": "With slug as key"
                },
                'false': {
                    "value": "false",
                    "summary": "Without slug as key"
                }
            },
            'allowEmptyValue': True,
            'description': 'Allows getting the question answers as an object with the slug as key, for easier processing. '
        }
    ]

    def update_cached_data(self):
        if not self.cached_data:
            self.cached_data = {}
        if getattr(config, 'ENABLE_ENTERPRISE_FEATURES', False):
            from mobile_sync_system.factories.survey_answer_factory import SurveyAnswerFactory
            self.cached_data['mobile_object'] = SurveyAnswerFactory.map_server_to_mobile_core(self)
        else:
            self.cached_data['mobile_object'] = {}

    @property
    def person_answering(self):
        if self.lead_answering:
            return self.lead_answering.person
        elif self.client_answering:
            return self.client_answering.person

    def getQuestionsInOrder(self):
        return self.surveyAnswered.getQuestions()

    def getCompletionPercentage(self):
        allQuestions = self.getQuestionsInOrder()
        answerCount = 0
        for Q in allQuestions:
            Answers = Q.getAnswersInSurveyAnswer(self)
            if Answers.count() != 0:
                answerCount += 1
        return (answerCount / allQuestions.count())

    def before_update(self):
        self.modifiedDate = datetime.now()
        if self.personAnswering != self.person_answering:
            self.personAnswering = self.person_answering
            self.check_first_last_coherence()
        self.check_coherence()
        self.update_cached_data()
    
    def before_insert(self):
        if not self.client_answering and not self.lead_answering:
            import config
            if not config.is_user_journey_editor_enabled():
                raise Exception('SurveyAnswer must have either lead or client answering')
        self.personAnswering = self.person_answering
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()
        self.check_coherence()
        self.check_first_last_coherence(insert=True)

    def after_insert(self):
        self.check_coherence() 
        self.check_first_last_coherence() # We need to check after insert too to avoid issues
        self.update_cached_data()

    def check_coherence(self):
        if self.personAnswering != self.person_answering:
            raise Error('Invalid person answering cache')
        if self.lead_answering and self.client_answering and self.lead_answering.person != self.client_answering.person:
            raise Error('Client and Lead are not the same person')
        
    def check_first_last_coherence(self, insert=False):
        if self.person_answering:
            person_id = self.person_answering.id
            form_id = self.surveyAnswered.form.id
            SurveyAnswer.check_first_last(form_id, person_id, current_answer=self, insert=insert)

    @staticmethod
    def check_first_last(form_id, person_answering_id, current_answer=None, insert=False):
        # It needs to be accross all versions of the form
        form_answers = list(SurveyAnswer.select().filter(lambda answer: answer.surveyAnswered.form.id == form_id and answer.personAnswering.id == person_answering_id).order_by(lambda answer: answer.started))
        # If we insert, the last answer is not there yet, so we need to add it to the list
        if insert and current_answer not in form_answers:
            form_answers.append(current_answer)
        if len(form_answers) == 0:
            first_answer = current_answer
            last_answer = current_answer
        else:
            first_answer = form_answers[0]
            last_answer = form_answers[-1]
        for a in form_answers:
            if a.is_first_answer and a != first_answer:
                a.is_first_answer = False
            if a.is_last_answer and a != last_answer:
                a.is_last_answer = False
        first_answer.is_first_answer = True
        last_answer.is_last_answer = True

    @classmethod
    def get_model_definition(cls, op, slug_as_keys=None, **kwargs):
        slug_as_keys = value_to_bool(slug_as_keys)
        return {
            'properties': {
                "id": {
                    "description": "The ID of the Form Answer",
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id
                },
                "form_id": {
                    "description": "The ID of the Form that is answered. It can be viewed in the Form editor next to the version number. Either this or form_version_uuid is required.",
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.surveyAnswered.id
                },
                "form_version_uuid": {
                    "description": "The UUID of the Form that is answered. Either this or form_id is required.",
                    "type": "string",
                    "example": "123e4567-e89b-12d3-a456-426614174000",
                    "value": lambda o: o.surveyAnswered.mobile_uuid
                },
                "start_time": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2020-09-01T14:34:54",
                    "description": "The date and time at which the form answering started",
                    "value": lambda o: o.started
                },
                "end_time": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2020-09-01T14:34:54",
                    "description": "The date and time at which the form answering finished",
                    "value": lambda o: o.ended
                },
                "subject_lead_id": {
                    "description": "The ID of the Client that answered the form (if any)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 1234,
                    "value": lambda o: o.lead_answering.id if o.lead_answering else None
                },
                "subject_client_id": {
                    "description": "The ID of the Client that answered the form (if any)",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 1234,
                    "value": lambda o: o.client_answering.id if o.client_answering else None
                },
                "discussed_topic_id": {
                    "description": "The ID of the Discussed Topic to which the form is related (if any).",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 1234,
                    "value": lambda o: o.discussed_topic.id if o.discussed_topic else None
                },
                "user_journey_run_step_id": {
                    "description": "The ID of the User Journey Run Step to which the form is related (if any).",
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "example": 1234,
                    "value": lambda o: o.user_journey_run_step.id if o.user_journey_run_step else None
                },
                "entry_user_id": {
                    "description": "The ID of the User that filled the form.",
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.interviewer.id if o.interviewer else None
                },
                "answers": {
                    "description": "The answers to the questions in the Form. The value is the answers to the question in the relevant format (string, number, etc.) or an array of the relevant format. ",
                    "oneOf": [{
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_name": {
                                    "description": "The name of the question (that can be obtained in the form editor in between parentheses)",
                                    "type": "string",
                                },
                                "answers": {
                                    "description": "The answers to the question in the relevant format (string, number, object, etc.) or an array of the answers in the relevant format if the question accepts multiple answers (even if just one answer was provided). ",
                                }
                            }
                        }}, 
                        {"type": "object"}
                    ],
                    "example": [{"question_name": "Child Name", "answers": "Matteo"}, {"question_name": "Age", "answers": 12}, {"question_name": "Favourite Colours", "answers": ["Green", "Blue"]}],
                    "value": lambda o: SurveyAnswerAnswersGetterService.get_answers_with_questions(o, new_format=True)
                } if not slug_as_keys else {
                    "description": "The answers to the questions in the Form. The key is the slug of the question and the value is the answers to the question in the relevant format (string, number, etc.) or an array of the relevant format. ",
                    "type": "object",
                    "example": {"child-name": "Matteo", "favourite-colours": ["Green", "Blue"]},
                    "value": lambda o: SurveyAnswerAnswersGetterService.get_answers_with_questions(o, slug_as_keys=True)
                },
                'skip_hook': {
                    "description": "If this is set to true, the `custom_form_answered` hook will not be sent as a result of that request (but will still get triggered by future requests). This is typically used to avoid loops of hooks with 3rd party applications.",
                    "oneOf": BOOLEAN_OPTIONAL_OPTIONS,
                    "example": False,
                    "value": lambda o: None
                },
                "modified_date": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2020-09-01T14:34:54",
                    "description": "The date and time at which the form answering finished",
                    "value": lambda o: o.modifiedDate
                },
            },
            'view_required': [],
            'view_allowed': [],
            'view_forbidden': ["skip_hook"],
            'edit_required': [],
            'edit_allowed': ["form_id", "start_time", "end_time", "subject_lead_id", "answers", "skip_hook", "use_names"],
            'create_allowed': ["form_id", "form_version_uuid","start_time", "end_time", "subject_lead_id", "subject_client_id", "discussed_topic_id", "answers", "skip_hook", "use_names"],
            'create_required': ["answers"],
            "no_docs": ["skip_hook"]
        }