import json
from datetime import datetime

from pony import orm

import config
if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.interaction_system.services.discussed_topic_getter_service import \
        DiscussedTopicGetterService
else:
    class _DiscussedTopicGetterServiceStub:
        """Gracefully skip discussed topic lookups when enterprise modules are absent."""

        @staticmethod
        def extract_from_user_and_id(*_, **__):
            return None

        @staticmethod
        def get_from_user_and_id(*_, **__):
            return None

    DiscussedTopicGetterService = _DiscussedTopicGetterServiceStub()
from core_system.client.services.client_getter_service import \
    ClientGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.helpers.date_helper import parse_datetime
from shared.logger.loggers import Error
from shared.services.base_service import BaseService
from survey_system.models.survey_answer import SurveyAnswer
from survey_system.models.survey_method import SurveyMethod
from survey_system.services.edit_answers_service import \
    EditSurveyAnswerAnswersService
from survey_system.services.error_message_service import \
    SurveyAnswerErrorMessageService
from survey_system.services.form_getter_service import (
    FormGetterService, FormVersionGetterService)
from survey_system.services.survey_answer_data_service import SurveyAnswerDataService
if config.ENABLE_ENTERPRISE_FEATURES:
    from app_builder_system.user_journey_editor.services.user_journey_run_service import UserJourneyRunStepService
else:
    class _UserJourneyRunStepServiceStub:
        """No-op user journey run lookups when enterprise editor is disabled."""

        @staticmethod
        def get_from_user_and_id(*_, **__):
            return None

    UserJourneyRunStepService = _UserJourneyRunStepServiceStub()
from survey_system.methods.helper import get_missing_questions


class SurveyAnswerService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, data, user, use_names=False):
        use_names=use_names or (not (data.get('use_ids', False) in [True, 'true']))
        try:
            this_answer = cls._add_from_data_and_user_core(data, user, use_names)
            return this_answer
        except Error as error:
            orm.rollback()
            error_message = SurveyAnswerErrorMessageService.get_human_readable_error(error)
            raise Error(error_message, code=error.code, **error.data) from error
        
    @classmethod
    def _edit_from_data_and_user(cls, answer, data, user, use_names=False):
        use_names=use_names or (not (data.get('use_ids', False) in [True, 'true']))
        try:
            this_answer = cls._edit_from_data_and_user_core(answer, data, user, use_names)
            return this_answer
        except Error as error:
            orm.rollback()
            error_message = SurveyAnswerErrorMessageService.get_human_readable_error(error)
            raise Error(error_message, code=error.code, **error.data) from error

    @classmethod
    def _add_from_data_and_user_core(cls, data, user, use_names=False):

        lead = LeadGetterService.extract_from_user_and_id(
            user, data, 'lead_id', strict=True, empty_allowed=True
        )
        if not lead:
            lead = LeadGetterService.extract_from_user_and_id(
                user, data, 'subject_lead_id', strict=True, empty_allowed=True
            )
        discussed_topic = DiscussedTopicGetterService.extract_from_user_and_id(
            user, data, 'discussed_topic_id', strict=True, empty_allowed=True
        )
        client = ClientGetterService.extract_from_user_and_id(
            user, data, 'client_id', strict=True, empty_allowed=True
        )
        if not client:
            client = ClientGetterService.extract_from_user_and_id(
                user, data, 'subject_client_id', strict=True, empty_allowed=True
            )
        if lead:
            person = lead.person
            if lead.installed:
                if not user.can_access('FillCustomFormsClients', person=person):
                    raise Error('INSUFFICIENT_PERMISSION', permission='FillCustomFormsClients')
            else:
                if not user.can_access('FillCustomFormsLeads', person=person):
                    raise Error('INSUFFICIENT_PERMISSION', permission='FillCustomFormsLeads')
        elif client:
            person = client.person
            # If there is a discussed topic, we check if the user can access addinteractions, otherwise we check if he can fillcustomformsclients
            if discussed_topic:
                if not user.can_access('AddInteractions', person=person):
                    raise Error('INSUFFICIENT_PERMISSION', permission='AddInteractions')
            elif not user.can_access('FillCustomFormsClients', person=person):
                raise Error('INSUFFICIENT_PERMISSION', permission='FillCustomFormsClients')
        else:
            import config
            if not config.is_user_journey_editor_enabled():
                raise Error("FORM_SUBJECT_REQUIRED")
            person = user.person

        start_time = parse_datetime(data.get('start_time')) or datetime.now()
        end_time = parse_datetime(data.get('end_time')) or datetime.now()
        form_version = None
        if 'form_version_id' in data:
            form_version = FormVersionGetterService.extract_from_user_and_id(
                user, data, 'form_version_id', strict=True, empty_allowed=True
            )
        if not form_version and 'form_version_uuid' in data:
            form_version = FormVersionGetterService.get_from_user_and_properties(user, strict=True, mobile_uuid=data['form_version_uuid'])
        if not form_version:
            form_version = FormVersionGetterService.extract_from_user_and_id(
                user, data, 'form_id', strict=True, empty_allowed=True
            )
            if not form_version:
                form = FormGetterService.extract_from_user_and_id(
                    user, data, 'wrapper_id', strict=True, empty_allowed=True
                )
                if form:
                    form_version = form.last_version
        if not form_version:
            raise Error('INVALID_FORM_ID')
        if lead:
            cls._check_if_form_editing_restricted(form_version, lead, user)

        survey_method_name = data.get('form_method', 'web_assisted')
        survey_method = SurveyMethod.get_by_name(survey_method_name)
        if not survey_method:
            if SurveyMethod.valid(survey_method_name):
                survey_method = survey_method_name
            else:
                raise Error('Unrecognised form method '+str(survey_method_name))

        survey_answer = SurveyAnswer(
            started=start_time,
            ended=end_time,
            client_answering=client,
            lead_answering=lead,
            interviewer=user.reload().person,
            surveyAnswered=form_version,
            surveyMethod=survey_method,
            discussed_topic=discussed_topic
        )
        mobile_uuid = data.get('mobile_uuid')
        if mobile_uuid:
            survey_answer.mobile_uuid = mobile_uuid

        skip_hook = data.get('skip_hook', False) in [True, 'true']
        raw_answers = data.get('answers')
        if isinstance(raw_answers, str):
            raw_answers = json.loads(raw_answers)
        EditSurveyAnswerAnswersService.add_survey_answer_answers(
            survey_answer, raw_answers, use_names, update_status=True,
            skip_hook=skip_hook, user=user
        )
        return survey_answer

    @classmethod
    def _edit_from_data_and_user_core(cls, answer, data, user, use_names=False):
        permission = 'AddInteractions' if answer.discussed_topic else 'FillCustomFormsClients' if answer.client_answering else 'FillCustomFormsLeads' if answer.lead_answering else 'FillCustomFormsUserJourney'
        lead = None
        person = answer.person_answering
        if not user.can_access(permission, person=person):
            raise Error('INSUFFICIENT_PERMISSION', permission=permission)

        if answer.lead_answering:
            cls._check_if_form_editing_restricted(
                answer.surveyAnswered, answer.lead_answering, user
            )
            
        if use_names:
            missing_questions = get_missing_questions(request_data=data)
            if missing_questions:
                raise Error(f"No question exists with the {'names' if len(missing_questions) > 1 else 'name'} {', '.join(missing_questions)}")
        
        if 'modifiedDate' in data:
            answer.modifiedDate = parse_datetime(data['modifiedDate'])

        if 'form_method' in data:
            answer.surveyMethod = data['form_method']

        if 'start_time' in data:
            answer.started = parse_datetime(data['start_time'])

        if 'end_time' in data:
            answer.ended = parse_datetime(data['end_time'])

        if 'subject_lead_id' in data:
            lead = LeadGetterService.extract_from_user_and_id(
                user, data, 'subject_lead_id', strict=True, empty_allowed=True
            )
            answer.lead_answering = lead if lead else answer.lead_answering

        answer.interviewer = user.reload().person

        answers = data.get('answers')
        if lead and lead.installed and not user.can_access('FillCustomFormsClients', person=person):
            raise Error('INSUFFICIENT_PERMISSION', permission='FillCustomFormsClients')
            
        if isinstance(answers, str):
            answers = json.loads(answers)
        if answers:
            skip_hook = data.get('skip_hook', False) in [True, 'true']
            EditSurveyAnswerAnswersService.edit_survey_answer_answers(
                answer, answers, use_names, skip_hook=skip_hook, user=user
            )
        return answer

    @classmethod
    def get_survey_answer_data_dict(cls, survey_answer, use_names):
        return SurveyAnswerDataService.get_survey_answer_data_dict(survey_answer, use_names)

    @classmethod
    def get_affected_entity(cls, data, user, **kwargs):
        if data.get('subject_lead_id'):
            lead = LeadGetterService.get_from_user_and_id(
                user, id=data['subject_lead_id'], strict=True)
            if lead:
                return lead.person.village
        if data.get('subject_client_id'):
            client = ClientGetterService.get_from_user_and_id(
                user, id=data['subject_client_id'], strict=True)
            if client:
                return client.person.village
        if data.get('discussed_topic_id'):
            discussed_topic = DiscussedTopicGetterService.get_from_user_and_id(
                user, id=data['discussed_topic_id'], strict=True)
            if discussed_topic:
                return discussed_topic.interaction.client.person.village
        if config.ENABLE_ENTERPRISE_FEATURES and data.get('user_journey_run_step_id'):
            user_journey_run_step = UserJourneyRunStepService.get_from_user_and_id(user, data.get('user_journey_run_step_id'))
            if user_journey_run_step:
                journey_run = user_journey_run_step.user_journey_run
                if journey_run.subject_client:
                    return journey_run.subject_client.person.village
                if journey_run.subject_lead:
                    return journey_run.subject_lead.person.village
                return user_journey_run_step.user.person.shop  # Not always there
        return None

    @classmethod
    def _check_if_form_editing_restricted(cls, form_version, lead, user):
        form = form_version.form
        lead_in_restricted_state = LeadStatusService.lead_is_in_restricted_status(lead)
        if form and form.restrict_editing and lead_in_restricted_state and not user.can_access('EditRestrictedPersonalDetailsLeads', person=lead.person):
            raise Error('INSUFFICIENT_PERMISSION', permission='EditRestrictedPersonalDetailsLeads')
        