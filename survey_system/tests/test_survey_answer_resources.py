from core_system.person.services.form_visibility_rule_getter import FormVisibilityRuleGetterService
from pony.orm import db_session
from config import API_PREFIX
from survey_system.models.survey_answer import SurveyAnswer
from mock import patch


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

