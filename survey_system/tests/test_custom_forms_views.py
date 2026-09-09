from datetime import datetime
import re

from flask import url_for
from pony.orm import db_session, flush

from core_system.client.models import Client
from core_system.core_entities import db
from core_system.operational_entities.models import Village
from core_system.person.models.person_model import Person, PersonType
from survey_system.form_editor.services import FormService
from survey_system.models.forms import Form
from survey_system.models.question import Question
from survey_system.models.survey_answer import SurveyAnswer
from survey_system.models.survey_method import SurveyMethod


class TestCustomFormsUpdateLoadsLatestVersion:
    """Regression for Update (creates a new version) loading the latest form version."""

    UNIQUE_QUESTION_LABEL = 'SB1107 customer consent'
    _form_seq = 0

    @classmethod
    def _create_client(cls):
        person = Person(
            name='SB1107',
            surname='Client',
            type=PersonType.client,
            village=Village.select().first(),
        )
        return Client(person=person, RegistrationDate=datetime.now())

    @classmethod
    def _create_answer_on_v1_then_publish_v2(cls):
        user = db.User.get(username='super_admin@test.com')
        existing_question = Question.select().first()
        assert user is not None
        assert existing_question is not None

        cls._form_seq += 1
        client = cls._create_client()
        form = Form(
            name=f'SB1107 Update Version Test Form {cls._form_seq}',
            icon='assignment',
            for_leads=True,
            for_clients=True,
            for_interactions=False,
        )
        v1 = FormService.create(
            form,
            [{
                'order': 1,
                'question': existing_question.id,
                'min_answers': 0,
                'max_answers': 1,
            }],
            user=user,
        )
        flush()

        answer = SurveyAnswer(
            surveyAnswered=v1,
            client_answering=client,
            started=datetime.now(),
            ended=datetime.now(),
            surveyMethod=SurveyMethod.web_assisted,
            is_last_answer=True,
            is_first_answer=True,
            interviewer=user.person,
        )
        flush()

        v1_question_id = v1.getQuestions().first().question.id
        v2 = FormService.create(
            form,
            [
                {
                    'order': 1,
                    'question': v1_question_id,
                    'min_answers': 0,
                    'max_answers': 1,
                },
                {
                    'order': 2,
                    'name': 'sb1107_customer_consent',
                    'type': 'text',
                    'text': cls.UNIQUE_QUESTION_LABEL,
                    'min_answers': 0,
                    'max_answers': 1,
                },
            ],
            user=user,
        )
        flush()
        return answer, v1, v2

    @staticmethod
    def _form_id_from_html(html):
        match = re.search(
            r'name="form_id:number"[^>]*value="(\d+)"|value="(\d+)"[^>]*name="form_id:number"',
            html,
        )
        assert match, 'form_id hidden input not found in rendered HTML'
        return int(match.group(1) or match.group(2))

    @db_session
    def test_update_loads_latest_form_version(self, context, super_admin_app):
        with context:
            answer, v1, v2 = self._create_answer_on_v1_then_publish_v2()
            assert answer.surveyAnswered.id == v1.id
            assert answer.surveyAnswered.form.last_version.id == v2.id

            response = super_admin_app.get(url_for(
                'custom_forms.custom_forms_answers_views',
                survey_answer_id=answer.id,
                action='update',
            ))
            assert response.status_code == 200
            html = response.get_data(as_text=True)

            assert self._form_id_from_html(html) == v2.id
            assert self.UNIQUE_QUESTION_LABEL in html
            assert '/forms/answers?use_ids=true' in html
            assert f'/forms/answers/{answer.id}?use_ids=true' not in html

    @db_session
    def test_edit_keeps_original_form_version(self, context, super_admin_app):
        with context:
            answer, v1, v2 = self._create_answer_on_v1_then_publish_v2()
            assert v1.id != v2.id

            response = super_admin_app.get(url_for(
                'custom_forms.custom_forms_answers_views',
                survey_answer_id=answer.id,
                action='edit',
            ))
            assert response.status_code == 200
            html = response.get_data(as_text=True)

            assert self._form_id_from_html(html) == v1.id
            assert self.UNIQUE_QUESTION_LABEL not in html
            assert f'/forms/answers/{answer.id}?use_ids=true' in html
