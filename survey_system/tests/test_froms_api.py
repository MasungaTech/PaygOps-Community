import json
from pony import orm
from config import API_PREFIX
from survey_system.models.forms import FormVersion
from survey_system.models.question import Question


class TestSurveysApiTest:
    url = '{}/surveys'.format(API_PREFIX)

    def test_get_returns_200(self, api_client, good_api_key):
        response = api_client.get(self.url, headers=self._header(good_api_key))

        assert 200 == response.status_code

    def test_get_returns_unauthorized(self, api_client):
        response = api_client.get(self.url)

        assert 401 == response.status_code

    @orm.db_session
    def test_get_returns_surveys(self, api_client, good_api_key):
        response = api_client.get(self.url, headers=self._header(good_api_key))

        assert FormVersion.select().count() == len(response.get_json())

    def _header(self, good_api_key):
        token = 'Bearer {}'.format(good_api_key)

        return {'Authorization': token}


class TestQuestionApiTest:
    url = '{}/questions/'.format(API_PREFIX)

    @orm.db_session
    def test_delete_returns_error(self, api_client, good_api_key):
        question = Question.select().first()

        url = f'{API_PREFIX}/questions/{question.id}'

        response = api_client.delete(url, headers=self._header(good_api_key))

        assert 400 == response.status_code

    @orm.db_session
    def test_get_returns_200(self, api_client, good_api_key):
        question = Question.select().first()
        url = f'{API_PREFIX}/questions/{question.id}'

        response = api_client.get(url, headers=self._header(good_api_key))
        data = json.loads(response.data)


        minValue = question.minValue if question.minValue else ''
        maxValue = question.maxValue if question.maxValue else ''

        assert 200 == response.status_code
        assert question.id == data.get('id')
        assert minValue == data.get('minValue')
        assert maxValue == data.get('maxValue')

    def _header(self, good_api_key):
        token = 'Bearer {}'.format(good_api_key)

        return {'Authorization': token}


class TestQuestionsApiTest:
    url = '{}/questions'.format(API_PREFIX)

    def test_get_returns_200(self, api_client, good_api_key):
        response = api_client.get(self.url, headers=self._header(good_api_key))

        assert 200 == response.status_code

    def test_get_returns_unauthorized(self, api_client):
        response = api_client.get(self.url)

        assert 401 == response.status_code

    @orm.db_session
    def test_get_returns_questions(self, api_client, good_api_key):
        response = api_client.get(self.url+'?filter=all', headers=self._header(good_api_key))
        questions = response.get_json()['questions']
        pagination = response.get_json()['pagination']
        assert 10 == len(questions)
        assert 10 == pagination['per_page']
        assert 1 == pagination['page']

    def _header(self, good_api_key):
        token = 'Bearer {}'.format(good_api_key)

        return {'Authorization': token}
