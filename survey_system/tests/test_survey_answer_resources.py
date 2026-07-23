from core_system.person.services.form_visibility_rule_getter import FormVisibilityRuleGetterService
from pony.orm import db_session
from config import API_PREFIX
from survey_system.models.survey_answer import SurveyAnswer
from survey_system.services.survey_answer_getter_service import SurveyAnswerGetterService
from mock import patch
from werkzeug.exceptions import Forbidden


class TestSurveyAnswerResources:
    TEST_FORM_ANSWER_ID = None
    FORM_ANSWER_DATA = {
        "form_id": 7,
        "start_time": "2017-09-12T10:51:38.981163Z",
        "end_time": "2017-09-12T10:51:38.981186Z",
        "form_method": "web_assisted",
        "subject_client_id": 1,
        "entry_user_id": 2,
        "answers": {
            "Reason for late payment": ["Other (fill explanation below)"],
            "Details on the late payment": ["This client is inactive because he forgot."],
            "Alternative lighting technology": ["D lights"],
            "Promise to pay": [2],
            "Recommendations Given Late Payment": ["Sell the crops earlier."]
        }
    }
    FORM_ANSWER_DATA_LAST = {
        "form_id": 7,
        "start_time": "2017-10-12T10:51:38.981163Z",
        "end_time": "2017-10-12T10:51:38.981186Z",
        "form_method": "web_assisted",
        "subject_client_id": 1,
        "entry_user_id": 1,
        "answers": {
            "Reason for late payment": ["Other (fill explanation below)"],
            "Details on the late payment": ["This client is inactive because he forgot."],
            "Alternative lighting technology": ["D lights"],
            "Promise to pay": [2],
            "Recommendations Given Late Payment": ["Sell the crops earlier."]
        }
    }
    FORM_ANSWER_DATA_EDITED = {
        "answers": {
            "Reason for late payment": ["Other (fill explanation below)"],
            "Details on the late payment": ["This client is inactive because he forgot this time."],
            "Alternative lighting technology": ["D lights and kerosene"],
            "Promise to pay": [7],
            "Recommendations Given Late Payment": ["Sell the crops earlier PLEASE!"]
        }
    }
    FORM_ANSWER_DATA_2 = {
        "form_id": 28,
        "start_time": "2017-11-03T19:21:42.535760Z",
        "end_time": "2017-11-03T19:21:42.535764Z",
        "form_method": "web_assisted",
        "subject_client_id": 1,
        "entry_user_id": 2,
        "answers": {
            "activity_group": [
                {
                    "activity_type": "Agricultural Sector",
                    "activity_name": "farmer",
                    "activity_income": 55000,
                    "activity_income_frequency": "Weekly"
                },
                {
                    "activity_type": "Service sector",
                    "activity_name": "business",
                    "activity_income": 15000,
                    "activity_income_frequency": "Weekly"
                }
            ]
        }
    }
    FORM_ANSWER_DATA_EDITED_2 = {
        "answers": {
            "activity_group": [
                {
                    "activity_type": "Service sector",
                    "activity_name": "M-Pesa shop",
                    "activity_income": 9999,
                    "activity_income_frequency": "Weekly"
                },
                {
                    "activity_type": "Mining Sector",
                    "activity_name": "Minor",
                    "activity_income": 111111,
                    "activity_income_frequency": "Monthly"
                }
            ]
        }
    }

    @classmethod
    def _post_data(cls, route, form_data, api_client, admin_api_key):
        response = api_client.post(API_PREFIX + route,
                                   json=form_data,
                                   headers={'Authorization': 'Bearer ' + admin_api_key})
        return response

    @classmethod
    def _get_data(cls, route, api_client, admin_api_key, params=None):
        response = api_client.get(API_PREFIX + route,
                                  headers={'Authorization': 'Bearer ' + admin_api_key,
                                           'Content-Type': 'application/json'},
                                  query_string=params)
        return response

    @classmethod
    def _check_if_data_in_dict_match(cls, dict1, dict2):
        for key, dict1_value in dict1.items():
            if isinstance(dict1_value, list):
                assert sorted(dict2.get(key)) == sorted(dict1_value)
            else:
                assert dict2.get(key) == dict1_value

    def test_add_form_answer_basic(self, api_client, admin_api_key):
        response = self._post_data('/forms/answers', self.FORM_ANSWER_DATA, api_client, admin_api_key)
        assert response.status_code == 201
        self.__class__.TEST_FORM_ANSWER_ID = response.json['id']
        print(self.FORM_ANSWER_DATA)
        print(response.json)
        self._check_if_data_in_dict_match(self.FORM_ANSWER_DATA, response.json)
        with db_session:
            first_answer = SurveyAnswer.get(id=response.json['id'])
            assert first_answer.is_last_answer
            assert first_answer.is_first_answer
        
        response = self._post_data('/forms/answers', self.FORM_ANSWER_DATA_LAST, api_client, admin_api_key)
        with db_session:
            last_answer = SurveyAnswer.get(id=response.json['id'])
            first_answer = SurveyAnswer.get(id=first_answer.id)
            assert last_answer.is_last_answer
            assert not last_answer.is_first_answer
            assert not first_answer.is_last_answer
            assert first_answer.is_first_answer

    def test_get_form_answer_basic(self, api_client, admin_api_key):
        url = '/forms/answers/'+str(self.__class__.TEST_FORM_ANSWER_ID)
        print(url)
        response = self._get_data(url, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match(self.FORM_ANSWER_DATA, response.json)

    def test_edit_form_answer_basic(self, api_client, admin_api_key):
        url = '/forms/answers/' + str(self.__class__.TEST_FORM_ANSWER_ID)
        response = self._post_data(url, self.FORM_ANSWER_DATA_EDITED, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match(self.FORM_ANSWER_DATA_EDITED, response.json)

    def test_add_form_answer_complex(self, api_client, admin_api_key):
        with patch.object(FormVisibilityRuleGetterService, "get_client_data_answers_id_for_client", return_value=[]):
            response = self._post_data('/forms/answers', self.FORM_ANSWER_DATA_2, api_client, admin_api_key)
            assert response.status_code == 201
            print(response.json)
            self.__class__.TEST_FORM_ANSWER_ID = int(response.json['id'])
            self._check_if_data_in_dict_match(self.FORM_ANSWER_DATA_2, response.json)

    def test_get_form_answer_complex(self, api_client, admin_api_key):
        url = '/forms/answers/'+str(self.__class__.TEST_FORM_ANSWER_ID)
        print(url)
        response = self._get_data(url, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match(self.FORM_ANSWER_DATA_2, response.json)

    def test_edit_form_answer_complex(self, api_client, admin_api_key):
        url = '/forms/answers/' + str(self.__class__.TEST_FORM_ANSWER_ID)
        response = self._post_data(url, self.FORM_ANSWER_DATA_EDITED_2, api_client, admin_api_key)
        assert response.status_code == 200
        print(self.FORM_ANSWER_DATA_EDITED_2)
        print(response.json)
        self._check_if_data_in_dict_match(self.FORM_ANSWER_DATA_EDITED_2, response.json)


class TestSurveyAnswerListResource:
    LIST_ROUTE = '/custom_forms/answers'

    @classmethod
    def _get_data(cls, route, api_client, token, params=None):
        return api_client.get(
            API_PREFIX + route,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
            query_string=params,
        )

    def test_list_by_form_id_and_subject_client_id(self, api_client, admin_api_key):
        passthrough = lambda user, **kwargs: kwargs
        with patch.object(SurveyAnswerGetterService, 'preprocess_list_filters', passthrough):
            with patch.object(SurveyAnswerGetterService, 'get_list', return_value=[101]) as get_list:
                list_response = self._get_data(
                    self.LIST_ROUTE,
                    api_client,
                    admin_api_key,
                    params={'form_id': '7', 'subject_client_id': '1'},
                )
        assert list_response.status_code == 200
        assert list_response.json == [101]
        assert get_list.call_args[1]['form_id'] == '7'
        assert get_list.call_args[1]['subject_client_id'] == '1'

    def test_list_with_date_range(self, api_client, admin_api_key):
        with patch.object(SurveyAnswerGetterService, 'get_list', return_value=[101]) as get_list:
            list_response = self._get_data(
                self.LIST_ROUTE,
                api_client,
                admin_api_key,
                params={
                    'start_time': '2017-09-01T00:00:00',
                    'end_time': '2017-09-30T23:59:59',
                },
            )
        assert list_response.status_code == 200
        assert 'start_time' in get_list.call_args[1]
        assert 'end_time' in get_list.call_args[1]

    def test_list_is_last_answer_filter(self, api_client, admin_api_key):
        with patch.object(SurveyAnswerGetterService, 'get_list', return_value=[202]) as get_list:
            list_response = self._get_data(
                self.LIST_ROUTE, api_client, admin_api_key, params={'is_last_answer': 'true'})
        assert list_response.status_code == 200
        assert get_list.call_args[1]['is_last_answer'] is True

    def test_list_permission_denied_without_view_form_answers(self, api_client, admin_api_key):
        with patch(
            'shared.api_helpers.base_api_class_all.check_permissions',
            side_effect=Forbidden('No sufficient permission'),
        ):
            response = self._get_data(self.LIST_ROUTE, api_client, admin_api_key)
        assert response.status_code == 403

    def test_list_pagination_boundaries(self, api_client, admin_api_key):
        with patch.object(SurveyAnswerGetterService, 'get_list', side_effect=[[11], [22]]):
            page_one = self._get_data(
                self.LIST_ROUTE, api_client, admin_api_key, params={'page': '1', 'page_size': '1'})
            page_two = self._get_data(
                self.LIST_ROUTE, api_client, admin_api_key, params={'page': '2', 'page_size': '1'})
        assert page_one.status_code == 200
        assert page_two.status_code == 200
        assert page_one.json == [11]
        assert page_two.json == [22]

    def test_list_include_objects_passes_serialization_params(self, api_client, admin_api_key):
        payload = [{'id': 5, 'form_id': 7, 'answers': []}]
        with patch.object(SurveyAnswerGetterService, 'get_list', return_value=payload) as get_list:
            listed = self._get_data(
                self.LIST_ROUTE,
                api_client,
                admin_api_key,
                params={'include_objects': 'true', 'slug_as_keys': 'true'},
            )
        assert listed.status_code == 200
        assert listed.json == payload
        assert get_list.call_args[1]['output'] == 'dict'
        assert get_list.call_args[1]['slug_as_keys'] == 'true'

    def test_list_answers_without_lead_or_client_when_unfiltered(self, api_client, admin_api_key):
        response = self._get_data(self.LIST_ROUTE, api_client, admin_api_key)
        assert response.status_code == 200
        assert isinstance(response.json, list)
