from core_system.operational_entities.models import Village
from config import API_PREFIX
from core_system.client.models import Client
from pony import orm


class TestEditClient:
    TEST_CLIENT_ID = None

    @orm.db_session
    def _get_client(self):
        return Client.select().first()

    def _post_edit_data(self, client_id, client_data, api_client, admin_api_key):
        response = api_client.post(API_PREFIX + '/clients/'+str(client_id),
                                   json=client_data,
                                   headers={'Authorization': 'Bearer ' + admin_api_key})
        return response

    @classmethod
    def _check_if_data_in_dict_match(cls, dict1, dict2):
        for key, dict1_value in dict1.items():
            if isinstance(dict1_value, list):
                assert sorted(dict2.get(key)) == sorted(dict1_value)
            else:
                assert dict2.get(key) == dict1_value

    def test_setup(self, api_client, admin_api_key):
        self.__class__.TEST_CLIENT_ID = self._get_client().id

    def test_edit_client_add_phone_number(self, api_client, admin_api_key):
        client_data = {
            'phone_numbers': ['+2348223334448'],
            'preferred_phone_number': '+2348223334448'
        }
        response = self._post_edit_data(self.__class__.TEST_CLIENT_ID, client_data, api_client, admin_api_key)
        assert response.status_code == 200
        print(client_data)
        self._check_if_data_in_dict_match(client_data, response.json)

    @orm.db_session
    def test_edit_client_data(self, api_client, admin_api_key):
        client_data = {
            'name': 'Example',
            'surname': 'EditClientModified',
            'village_id': int(Village.select().first().code),
            'gender': 'Female',
            'birthdate': '1991-02-21T15:32:22Z',
            'gps_longitude': 1.4,
            'gps_latitude': 1.6,
            'phone_numbers': ['+2349112223339'],
            'preferred_phone_number': '+2349112223339',
            "note": 'A good client',
            "portfolio_id": 1,
            "sms_language": "FR",
            "verbal_language": "Pirate English"
        }
        response = self._post_edit_data(self.__class__.TEST_CLIENT_ID, client_data, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match(client_data, response.json)
