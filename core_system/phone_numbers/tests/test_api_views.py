from config import API_PREFIX

class TestPhoneNumberAPIViews:

    def test_get_phone_number(self, api_client, good_api_key):
        response = api_client.get(API_PREFIX+'/phone_numbers/preferred',
                                  headers={'Authorization': 'Bearer '+good_api_key})
        assert response.status_code == 200

    def test_get_phone_number_with_param(self, api_client, good_api_key):
        response = api_client.get(API_PREFIX+'/phone_numbers/preferred',
                                  data={'client_id': 23},
                                  headers={'Authorization': 'Bearer '+good_api_key})
        assert response.status_code == 200
