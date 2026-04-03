import json
from survey_system.models.question_type import QuestionType
from pony import orm

from config import API_PREFIX

from survey_system.models.forms import FormVersion
from survey_system.services.other_services import QuestionService


class TestFormCreatorApiTest:
    url = '{}/forms'.format(API_PREFIX)

    @orm.db_session
    def test_create_form(self, api_client, good_api_key):
        expected_length = FormVersion.select().count() + 1

        data = self._request_data()
        headers = _authorization_header(good_api_key)
        headers['Content-type'] = 'application/json'
        response = api_client.post(self.url, data=json.dumps(data), headers=headers)
        json_response = response.get_json()

        expected_response_fields = ['id', 'updated_by', 'update_date', 'version']

        body_keys = list(json_response.keys())
        has_required_fields = all(key in body_keys for key in expected_response_fields)
        assert has_required_fields
        assert response.status_code == 201
        assert expected_length == FormVersion.select().count()

    @orm.db_session
    def test_post_invalid_data_returns_404(self, api_client, good_api_key):
        data = self._request_data()
        del data['name']
        invalid_data = data

        headers = _authorization_header(good_api_key)
        headers['Content-type'] = 'application/json'

        response = api_client.post(self.url, data=json.dumps(invalid_data), headers=headers)
        json_response = response.get_json()
        assert response.status_code == 400

    @orm.db_session
    def test_post_returns_unauthorized(self, api_client):
        data = self._request_data()
        headers = _authorization_header('Wrong')
        headers['Content-type'] = 'application/json'

        response = api_client.post(self.url, data=json.dumps(data), headers=headers)

        assert response.status_code == 401

    @staticmethod
    def _request_data():
        return {
            "name": "formTest",
            "icon": "battery_full",
            "questions": [
                {
                    "order": 1,
                    "question": 1,
                    "min_answers": 0,
                    "max_answers": 1
                }
            ]
        }


class TestQuestionsListApi:
    url = '{}/questions_formatted'.format(API_PREFIX)

    @orm.db_session
    def test_get_all_questions(self, api_client, good_api_key):
        response = api_client.get(self.url, headers=_authorization_header(good_api_key))

        json_response = response.get_json()
        expected_length = QuestionService.get_all_questions().filter(lambda q: q.type != QuestionType.group).count()

        assert len(json_response) == expected_length
        assert response.status_code == 200

    def test_get_returns_unauthorized(self, api_client):
        response = api_client.get(self.url, headers=_authorization_header('Wrong'))

        assert response.status_code == 401


class TestRetrieveFormApi:
    url = '{}/forms/{}'

    def test_given_non_existent_form_returns_404(self, api_client, good_api_key):
        non_form_url = self.url.format(API_PREFIX, 'NaN')
        response = api_client.get(non_form_url, headers=_authorization_header(good_api_key))

        assert response.status_code == 404

    @orm.db_session
    def test_get_return_form(self, api_client, good_api_key):
        form_id = FormVersion.select().first().id

        form_url = self.url.format(API_PREFIX, form_id)
        response = api_client.get(form_url, headers=_authorization_header(good_api_key))

        expected_response_fields = ['id', 'version', 'name', 'icon', 'questions']
        json_response = response.get_json()
        body_keys = list(json_response.keys())
        has_required_fields = all(key in body_keys for key in expected_response_fields)
        assert has_required_fields
        assert response.status_code == 200

    @orm.db_session
    def test_get_returns_unauthorized(self, api_client):
        form_id = FormVersion.select().first().id

        form_url = self.url.format(API_PREFIX, form_id)
        response = api_client.get(form_url, headers=_authorization_header('Wrong'))

        assert response.status_code == 401


class TestUpdateForm:
    url = '{}/forms/{}'

    @orm.db_session
    def test_without_proper_permission_returns_unauthorized(self, api_client):
        form_id = FormVersion.select().first().id

        form_url = self.url.format(API_PREFIX, form_id)
        response = api_client.put(form_url, headers=_authorization_header('Wrong'))

        assert response.status_code == 401

    def test_form_does_not_exist_returns_404(self, api_client, good_api_key):
        form_url = self.url.format(API_PREFIX, 'WRONG_FORM_ID')
        response = api_client.put(form_url, headers=_authorization_header(good_api_key))

        assert response.status_code == 404

    @orm.db_session
    def test_put_when_invalid_data_returns_400(self, api_client, good_api_key):
        form_id = FormVersion.select().first().id
        form_url = self.url.format(API_PREFIX, form_id)

        headers = _authorization_header(good_api_key)
        headers['Content-type'] = 'application/json'

        response = api_client.put(form_url, data=json.dumps({"wrong_body": "WRONG"}), headers=headers)
        json_response = response.get_json()
        expected_response = {'success': False, 'error': "Name is required", 'error_data': {}, 'error_message': 'Name is required'}
        assert json_response == expected_response
        assert response.status_code == 400


def _authorization_header(good_api_key):
    token = 'Bearer {}'.format(good_api_key)

    return {'Authorization': token}
