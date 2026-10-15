from datetime import datetime, timedelta

import config
from pony.orm import exists, select

from core_system.client.services.client_getter_service import ClientGetterService
from core_system.users.models.user_model import User
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.helpers.form_helpers import value_to_bool
from shared.services.base_getter_service import BaseGetterService
from survey_system.models.answer import Answer
from survey_system.models.survey_answer import SurveyAnswer


class SurveyAnswerGetterService(BaseGetterService):

    OBJ_NAME = 'Form Answer'

    @classmethod
    def preprocess_list_filters(cls, user, **kwargs):
        for bool_key in ('is_last_answer', 'is_first_answer'):
            if bool_key in kwargs and kwargs[bool_key] is not None:
                kwargs[bool_key] = value_to_bool(kwargs[bool_key])
        if kwargs.get('subject_lead_id') is not None:
            lead = LeadGetterService.get_from_user_and_id(
                user, kwargs['subject_lead_id'], strict=True, main_resource=True)
            kwargs['subject_lead_id'] = lead.id
        if kwargs.get('subject_client_id') is not None:
            client = ClientGetterService.get_from_user_and_id(
                user, kwargs['subject_client_id'], strict=True, main_resource=True)
            kwargs['subject_client_id'] = client.id
        if config.ENABLE_ENTERPRISE_FEATURES and kwargs.get('discussed_topic_id') is not None:
            from after_sales_system.interaction_system.services.discussed_topic_getter_service import (
                DiscussedTopicGetterService,
            )
            discussed_topic = DiscussedTopicGetterService.get_from_user_and_id(
                user, kwargs['discussed_topic_id'], strict=True, main_resource=True)
            kwargs['discussed_topic_id'] = discussed_topic.id
        if kwargs.get('answered_by_user_id') is not None:
            interviewer_user = User.get(id=int(kwargs['answered_by_user_id']))
            if not interviewer_user or not interviewer_user.person:
                cls.raise_strict(main_resource=True, user=user, id=kwargs['answered_by_user_id'])
            kwargs['answered_by_user_id'] = interviewer_user.person.id
        return kwargs

    @classmethod
    def get_list(cls, current_user=None, output='objects', page=None, page_size=1000, model=None,
                 ordered=False, alternate_model=None, **kwargs):
        serialize_params = SurveyAnswer.parse_parameters(kwargs)
        filter_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in serialize_params and k not in ('alternate_model',)
        }
        objects = cls.get_filtered_objects(current_user, **filter_kwargs)
        objects = objects.order_by(lambda sa: (sa.started, sa.id))
        if model:
            filter_kwargs['model'] = model
        if alternate_model:
            filter_kwargs['alternate_model'] = alternate_model
        if page is not None:
            objects = objects.page(page, page_size)
        if output == 'dict':
            objects = objects[:]
            return [
                obj.get_serialized_object(
                    model=model or SurveyAnswer,
                    alternate_model=alternate_model,
                    **serialize_params,
                )
                for obj in objects
            ]
        if output == 'objects':
            return objects
        return [getattr(obj, output) for obj in objects]

    @classmethod
    def _collect_visible_answer_ids(cls, current_user):
        current_user = current_user.reload()
        if current_user.can_access_in_all('ViewFormAnswers'):
            return None

        lead_ids = select(l.id for l in LeadGetterService.get_list(current_user))[:]
        client_ids = select(c.id for c in ClientGetterService.get_list(current_user))[:]
        answer_ids = set()
        if lead_ids:
            answer_ids.update(
                select(sa.id for sa in SurveyAnswer if sa.lead_answering.id in lead_ids)[:]
            )
        if client_ids:
            answer_ids.update(
                select(sa.id for sa in SurveyAnswer if sa.client_answering.id in client_ids)[:]
            )
        if config.ENABLE_ENTERPRISE_FEATURES:
            cached_ids = {}
            discussed_topics = current_user.get_discussed_topics_for_mobile(cached_ids)
            discussed_topic_ids = select(dt.id for dt in discussed_topics)[:]
            if discussed_topic_ids:
                answer_ids.update(
                    select(sa.id for sa in SurveyAnswer if sa.discussed_topic.id in discussed_topic_ids)[:]
                )
        person_id = current_user.person.id
        answer_ids.update(
            select(
                sa.id for sa in SurveyAnswer
                if not sa.lead_answering
                and not sa.client_answering
                and (not config.ENABLE_ENTERPRISE_FEATURES or not sa.discussed_topic)
                and sa.interviewer.id == person_id
            )[:]
        )
        return answer_ids

    @classmethod
    def get_filtered_objects(
        cls,
        current_user,
        form_id=None,
        form_version_id=None,
        subject_client_id=None,
        subject_lead_id=None,
        discussed_topic_id=None,
        answered_by_user_id=None,
        start_time=None,
        end_time=None,
        date=None,
        is_last_answer=None,
        is_first_answer=None,
        includes_question_name=None,
        includes_question_slug=None,
        includes_answer_value=None,
        includes_question_type=None,
        **kwargs,
    ):
        visible_ids = cls._collect_visible_answer_ids(current_user)
        if visible_ids is None:
            answers = SurveyAnswer.select()
        elif visible_ids:
            answers = SurveyAnswer.select(lambda sa: sa.id in visible_ids)
        else:
            answers = SurveyAnswer.select(lambda sa: sa.id == -1)

        if form_id is not None:
            answers = answers.filter(lambda sa: sa.surveyAnswered.form.id == int(form_id))
        if form_version_id is not None:
            answers = answers.filter(lambda sa: sa.surveyAnswered.id == int(form_version_id))
        if subject_lead_id is not None:
            answers = answers.filter(lambda sa: sa.lead_answering.id == int(subject_lead_id))
        if subject_client_id is not None:
            answers = answers.filter(lambda sa: sa.client_answering.id == int(subject_client_id))
        if discussed_topic_id is not None and config.ENABLE_ENTERPRISE_FEATURES:
            answers = answers.filter(lambda sa: sa.discussed_topic.id == int(discussed_topic_id))
        if answered_by_user_id is not None:
            answers = answers.filter(lambda sa: sa.interviewer.id == int(answered_by_user_id))
        if start_time is not None:
            answers = answers.filter(lambda sa: sa.started is not None and sa.started >= start_time)
        if end_time is not None:
            answers = answers.filter(lambda sa: sa.started is not None and sa.started <= end_time)
        if date is not None:
            if isinstance(date, datetime):
                day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                day_start = datetime.combine(date, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            answers = answers.filter(
                lambda sa: sa.started is not None and sa.started >= day_start and sa.started < day_end
            )
        if is_last_answer is not None:
            answers = answers.filter(lambda sa: sa.is_last_answer == is_last_answer)
        if is_first_answer is not None:
            answers = answers.filter(lambda sa: sa.is_first_answer == is_first_answer)
        if includes_question_name:
            name = includes_question_name
            answers = answers.filter(
                lambda sa: exists(
                    a for a in Answer
                    if a.surveyAnswer == sa and a.question.name == name
                )
            )
        if includes_question_slug:
            slug = includes_question_slug
            answers = answers.filter(
                lambda sa: exists(
                    a for a in Answer
                    if a.surveyAnswer == sa and a.question.slug == slug
                )
            )
        if includes_question_type is not None:
            question_type = int(includes_question_type)
            answers = answers.filter(
                lambda sa: exists(
                    a for a in Answer
                    if a.surveyAnswer == sa and a.question.type == question_type
                )
            )
        if includes_answer_value is not None:
            value = str(includes_answer_value)
            answers = answers.filter(
                lambda sa: exists(
                    a for a in Answer
                    if a.surveyAnswer == sa and a.value_text == value
                )
            )
        return answers

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
        return SurveyAnswer.select().filter(
            lambda sa: sa.surveyAnswered.form.id == form_id and sa.personAnswering == person
        )
