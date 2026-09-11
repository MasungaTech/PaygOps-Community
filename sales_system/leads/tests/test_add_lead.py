from datetime import datetime
from core_system.operational_entities.models import Village
from pony.orm import db_session
from config import API_PREFIX


class TestAddLead:

    @classmethod
    def _post_data(cls, lead_data, api_client, admin_api_key):
        response = api_client.post(API_PREFIX + '/leads',
                                   json=lead_data,
                                   headers={'Authorization': 'Bearer ' + admin_api_key})
        return response

    @classmethod
    def _check_if_data_in_dict_match(cls, dict1, dict2):
        print(dict2)
        for key, dict1_value in dict1.items():
            if isinstance(dict1_value, list):
                assert sorted(dict2.get(key)) == sorted(dict1_value)
            else:
                assert dict2.get(key) == dict1_value

    @db_session
    def test_add_lead_minimum_data_status_id(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'Lead',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'gender': "Male",
            'status': 14,
            'preferred_phone_number': '+2341234123493'
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 201, response.json
        expected_data = lead_data
        expected_data.update({'status': 'Very Interested'}) # This is changed when status is int
        self._check_if_data_in_dict_match(expected_data, response.json)

    @db_session
    def test_add_lead_minimum_data_text_status(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'Lead',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            "gender": "Male",
            'status': 'Ready to Buy',
            'preferred_phone_number': '+2341234123412'
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 201
        self._check_if_data_in_dict_match(lead_data, response.json)

    @db_session
    def test_add_lead_full_data(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'Lead',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 14,
            'generation_date': '2018-12-13T14:32:22Z',
            'status_comment': 'Its a good lead!',
            'next_contact': '2018-12-17T14:32:22Z',
            'reasons_for_not_buying': [111, 113],
            'offer': 888,
            'home': True,
            'business': True,
            'gender': 'Male',
            'birthdate': '1991-02-21T14:32:22Z',
            'gps_longitude': 1.2,
            'gps_latitude': 1.3,
            'phone_numbers': ['+2341112223333', '+2342223334444'],
            'preferred_phone_number': '+2342223334444',
            "promised_to_pay_date": "2019-01-08T00:00:00Z",
            "planned_delivery_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),   
            "commission": 1234,
            "commission_note": "Regular comission",
            "portfolio": 1,
            "sms_language": "FR",
            "verbal_language": "Pirate English"
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 201, response.json
        expected_data = lead_data
        expected_data.update({'status': 'Very Interested'})  # This is changed when status is int
        expected_data.update({'reasons_for_not_buying': ['Waiting for other income', 'Need to speak to family']})
        self._check_if_data_in_dict_match(expected_data, response.json)
        assert response.json['offer_id'] == 888

    @db_session
    def test_add_lead_data_text(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example2',
            'surname': 'Lead2',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 'Very Interested',
            'generation_date': '2018-12-13T14:32:22Z',
            'status_comment': 'Its a good lead!',
            'reasons_for_not_buying': ['Waiting for other income', 'Need to speak to family'],
            'offer': 888,
            'home': True,
            'gender': 'Male',
            'birthdate': '1991-02-21T14:32:22Z',
            'phone_numbers': ['+2345112223333', '+2345223334444'],
            'preferred_phone_number': '+2345223334444'
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 201
        self._check_if_data_in_dict_match(lead_data, response.json)
        assert response.json['offer_id'] == 888

    @db_session
    def test_add_lead_with_offer_id(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'LeadOfferId',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'gender': "Male",
            'status': 14,
            'preferred_phone_number': '+2341234123494',
            'offer_id': 888,
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 201, response.json
        assert response.json['offer_id'] == 888
        assert response.json['offer'] == 888

    def test_add_lead_village_missing(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'Lead',
            'generator': 1,
            'status': 14
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'VILLAGE_REQUIRED', response.json

    def test_add_lead_invalid_village(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'Lead',
            'village': -3,
            'generator': 1,
            'status': 14
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'INVALID_VILLAGE_ID'

    @db_session
    def test_add_lead_generator_missing(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'Lead',
            'village': Village.select().first().not_empty_code,
            'status': 14
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        print(response.status_code)
        print(response.json)
        assert response.status_code == 400
        assert "No Lead Generator ID was provided" in response.json['error_message']

    @db_session
    def test_add_lead_status_missing(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'Lead',
            'village': Village.select().first().not_empty_code,
            'generator': 1
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert "'status' is a required property" in response.json['error_message']

    @db_session
    def test_add_lead_status_invalid(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'Lead',
            'village': Village.select().first().not_empty_code,
            'gender': "Male",
            'status': -3,
            'generator': 1
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'INVALID_LEAD_STATUS_ID'

    @db_session
    def test_add_lead_status_forbidden(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'Lead',
            'village': Village.select().first().not_empty_code,
            "gender": "Male",
            'status': 3,
            'generator': 1
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'FORBIDDEN_STATUS_FOR_NEW_LEAD'

    @db_session
    def test_add_lead_name_missing(self, api_client, admin_api_key):
        lead_data = {
            'surname': 'Lead',
            'village': Village.select().first().not_empty_code,
            'gender': "Male",
            'status': 14,
            'generator': 1
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'first_name is a required field'

    @db_session
    def test_add_lead_surname_missing(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'village': Village.select().first().not_empty_code,
            "gender": "Male",
            'status': 14,
            'generator': 1
        }
        response = self._post_data(lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'surname is a required field'

    @db_session
    def test_add_lead_phone_too_short(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'WrongPhone',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 14,
            "gender": "Male",
            'phone_numbers': ['+234222333444'],
            'preferred_phone_number': '+234222333444'
        }
        response = self._post_data(lead_data, api_client, admin_api_key) # We make the duplicate
        assert response.status_code == 400
        assert response.json['error'] == 'PHONE_NUMBER_TOO_SHORT'

    @db_session
    def test_add_lead_phone_too_long(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'WrongPhone',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 14,
            "gender": "Male",
            'phone_numbers': ['+23422233344455'],
            'preferred_phone_number': '+23422233344455'
        }
        response = self._post_data(lead_data, api_client, admin_api_key) # We make the duplicate
        assert response.status_code == 400
        assert response.json['error'] == 'PHONE_NUMBER_TOO_LONG'
        
    @db_session
    def test_add_lead_phone_wrong_extension(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'WrongPhone',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 14,
            "gender": "Male",
            'phone_numbers': ['+1342223334445'],
            'preferred_phone_number': '+1342223334445'
        }
        response = self._post_data(lead_data, api_client, admin_api_key) # We make the duplicate
        assert response.status_code == 400
        assert response.json['error'] == 'INVALID_PHONE_NUMBER_EXTENSION'

    @db_session
    def test_add_lead_phone_already_owned(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'AlreadyOwnedPhone1',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 14,
            "gender": "Male",
            'phone_numbers': ['+2342223334446'],
            'preferred_phone_number': '+2342223334446'
        }
        self._post_data(lead_data, api_client, admin_api_key) # We create the first one
        lead_data = {
            'name': 'Example',
            'surname': 'AlreadyOwnedPhone2',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            "gender": "Male",
            'status': 14,
            'phone_numbers': ['+2342223334446'],
            'preferred_phone_number': '+2342223334446'
        }
        response = self._post_data(lead_data, api_client, admin_api_key) # We a second lead with the same number
        assert response.status_code == 400
        assert response.json['error'] == 'PHONE_NUMBER_ALREADY_OWNED'
