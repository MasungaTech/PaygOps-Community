from datetime import datetime

import pytest
from core_system.client.models import Client
from core_system.core_entities import db
from pony.orm import db_session, flush
from survey_system.models.forms import FormVersion
from survey_system.models.survey_answer import SurveyAnswer
from survey_system.models.survey_method import SurveyMethod
from survey_system.services.survey_answer_getter_service import SurveyAnswerGetterService


class TestSurveyAnswerGetterServiceFilters:

    @classmethod
    def _create_pair(cls):
        with db_session:
            client = Client.select().first()
            form_version = FormVersion.select().first()
            user = db.User.get(username='super_admin@test.com')
            if not client or not form_version or not user:
                return None
            started_first = datetime(2017, 9, 12, 10, 51, 38)
            started_last = datetime(2017, 10, 12, 10, 51, 38)
            first = SurveyAnswer(
                surveyAnswered=form_version,
                client_answering=client,
                started=started_first,
                ended=started_first,
                surveyMethod=SurveyMethod.web_assisted,
                is_last_answer=False,
                is_first_answer=True,
                interviewer=user.person,
            )
            last = SurveyAnswer(
                surveyAnswered=form_version,
                client_answering=client,
                started=started_last,
                ended=started_last,
                surveyMethod=SurveyMethod.web_assisted,
                is_last_answer=True,
                is_first_answer=False,
                interviewer=user.person,
            )
            flush()
            first = SurveyAnswer.select(
                lambda sa: sa.client_answering == client and sa.started == started_first
            ).first()
            last = SurveyAnswer.select(
                lambda sa: sa.client_answering == client and sa.started == started_last
            ).first()
            if not first or not last:
                return None
            return {
                'first_id': first.id,
                'last_id': last.id,
                'form_id': form_version.form.id,
                'client_id': client.id,
                'started_first': started_first,
            }

    def test_filter_by_form_and_client(self, super_admin_user):
        sample = self._create_pair()
        if not sample:
            pytest.skip('Test database missing client, form version, or admin user')
        with db_session:
            answers = SurveyAnswerGetterService.get_filtered_objects(
                super_admin_user(),
                form_id=sample['form_id'],
                subject_client_id=sample['client_id'],
            )
            ids = {a.id for a in answers}
            assert sample['first_id'] in ids
            assert sample['last_id'] in ids

    def test_filter_by_date_range(self, super_admin_user):
        sample = self._create_pair()
        if not sample:
            pytest.skip('Test database missing client, form version, or admin user')
        with db_session:
            in_range = SurveyAnswerGetterService.get_filtered_objects(
                super_admin_user(),
                start_time=datetime(2017, 9, 1),
                end_time=datetime(2017, 9, 30, 23, 59, 59),
            )
            assert sample['first_id'] in {a.id for a in in_range}
            out_range = SurveyAnswerGetterService.get_filtered_objects(
                super_admin_user(),
                start_time=datetime(2018, 1, 1),
                end_time=datetime(2018, 1, 2),
            )
            assert sample['first_id'] not in {a.id for a in out_range}

    def test_filter_is_last_answer(self, super_admin_user):
        sample = self._create_pair()
        if not sample:
            pytest.skip('Test database missing client, form version, or admin user')
        with db_session:
            last_only = SurveyAnswerGetterService.get_filtered_objects(
                super_admin_user(), is_last_answer=True)
            last_only_ids = {a.id for a in last_only}
            for answer_id in (sample['first_id'], sample['last_id']):
                answer = SurveyAnswer.get(id=answer_id)
                if answer.is_last_answer:
                    assert answer_id in last_only_ids
                else:
                    assert answer_id not in last_only_ids
