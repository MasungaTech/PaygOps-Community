from uuid import uuid4

import pytest
from pony import orm

from config import API_PREFIX
from survey_system.models.forms import Form
from survey_system.services.form_version_edit_service import FormVersionEditService


def _auth_header(api_key):
    return {'Authorization': 'Bearer {}'.format(api_key)}


def _unique_form_name():
    return 'availability-test-{}'.format(uuid4().hex[:12])


def _create_form(name=None, icon='', for_leads=True, for_clients=True, for_interactions=False):
    with orm.db_session:
        form = Form(
            name=name or _unique_form_name(),
            icon=icon,
            for_leads=for_leads,
            for_clients=for_clients,
            for_interactions=for_interactions,
        )
        orm.flush()
        return {
            'id': form.id,
            'name': form.name,
            'icon': form.icon,
            'for_leads': form.for_leads,
            'for_clients': form.for_clients,
            'for_interactions': form.for_interactions,
        }


def _minimal_question(name=None):
    question_name = name or 'availability-question-{}'.format(uuid4().hex[:12])
    return {
        'name': question_name,
        'text': question_name,
        'type': 'text',
        'min_answers': 0,
        'max_answers': 1,
    }


class TestFormVersionEditFromData:
    @orm.db_session
    def test_sets_for_interactions_from_available_for_interactions(self):
        form = Form(
            name=_unique_form_name(),
            for_leads=False,
            for_clients=False,
            for_interactions=False,
        )

        FormVersionEditService._edit_from_data_and_user(
            form=form,
            data_dict={'available_for_interactions': True},
            user=None,
        )

        assert form.for_interactions is True
        assert form.for_leads is False
        assert form.for_clients is False

    @orm.db_session
    def test_sets_explicit_false_for_interactions(self):
        form = Form(
            name=_unique_form_name(),
            for_leads=True,
            for_clients=True,
            for_interactions=True,
        )

        FormVersionEditService._edit_from_data_and_user(
            form=form,
            data_dict={'available_for_interactions': False},
            user=None,
        )

        assert form.for_interactions is False
        assert form.for_leads is True
        assert form.for_clients is True

    @orm.db_session
    def test_maps_all_availability_fields(self):
        form = Form(
            name=_unique_form_name(),
            for_leads=False,
            for_clients=False,
            for_interactions=False,
        )

        FormVersionEditService._edit_from_data_and_user(
            form=form,
            data_dict={
                'available_for_leads': True,
                'available_for_clients': True,
                'available_for_interactions': True,
            },
            user=None,
        )

        assert form.for_leads is True
        assert form.for_clients is True
        assert form.for_interactions is True

    @orm.db_session
    def test_omitted_keys_do_not_clear_existing_values(self):
        form = Form(
            name='keep-this-name',
            icon='',
            for_leads=True,
            for_clients=True,
            for_interactions=False,
        )

        FormVersionEditService._edit_from_data_and_user(
            form=form,
            data_dict={'available_for_interactions': True},
            user=None,
        )

        assert form.name == 'keep-this-name'
        assert form.icon == ''
        assert form.for_leads is True
        assert form.for_clients is True
        assert form.for_interactions is True


class TestFormVersionsAvailabilityApi:
    url = '{}/form_versions'.format(API_PREFIX)

    @pytest.mark.parametrize('available_for_interactions, initial_value', [
        (True, False),
        (False, True),
    ])
    def test_post_new_version_applies_available_for_interactions(
        self, api_client, good_api_key, available_for_interactions, initial_value
    ):
        form = _create_form(for_interactions=initial_value)

        response = api_client.post(
            self.url,
            headers=_auth_header(good_api_key),
            json={
                'form_id': form['id'],
                'available_for_interactions': available_for_interactions,
                'questions': [_minimal_question()],
            },
        )

        assert response.status_code == 201, response.get_json()
        assert response.get_json()['available_for_interactions'] is available_for_interactions

        with orm.db_session:
            updated_form = Form.get(id=form['id'])
            assert updated_form.for_interactions is available_for_interactions

    def test_post_new_version_without_availability_leaves_existing_flags(
        self, api_client, good_api_key
    ):
        form = _create_form(for_leads=True, for_clients=False, for_interactions=False)

        response = api_client.post(
            self.url,
            headers=_auth_header(good_api_key),
            json={
                'form_id': form['id'],
                'questions': [_minimal_question()],
            },
        )

        assert response.status_code == 201, response.get_json()
        body = response.get_json()
        assert body['available_for_leads'] is True
        assert body['available_for_clients'] is False
        assert body['available_for_interactions'] is False

        with orm.db_session:
            updated_form = Form.get(id=form['id'])
            assert updated_form.for_leads is True
            assert updated_form.for_clients is False
            assert updated_form.for_interactions is False

    def test_partial_edit_availability_does_not_clear_other_fields(
        self, api_client, good_api_key
    ):
        form = _create_form(
            name='keep-form-name-{}'.format(uuid4().hex[:8]),
            for_leads=True,
            for_clients=True,
            for_interactions=False,
        )
        create_response = api_client.post(
            self.url,
            headers=_auth_header(good_api_key),
            json={
                'form_id': form['id'],
                'questions': [_minimal_question()],
            },
        )
        assert create_response.status_code == 201, create_response.get_json()
        form_version_id = create_response.get_json()['id']

        response = api_client.post(
            '{}/{}'.format(self.url, form_version_id),
            headers=_auth_header(good_api_key),
            json={'available_for_interactions': True},
        )

        assert response.status_code == 200, response.get_json()
        body = response.get_json()
        assert body['available_for_interactions'] is True
        assert body['available_for_leads'] is True
        assert body['available_for_clients'] is True
        assert body['name'] == form['name']

        with orm.db_session:
            updated_form = Form.get(id=form['id'])
            assert updated_form.for_interactions is True
            assert updated_form.for_leads is True
            assert updated_form.for_clients is True
            assert updated_form.name == form['name']
