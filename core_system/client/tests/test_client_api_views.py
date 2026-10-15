from config import API_PREFIX


class TestClientAPIViews:
    def test_get_client_list(self, api_client, good_api_key):
        response = api_client.get(API_PREFIX + '/clients/simple_list',
                                  headers={'Authorization': 'Bearer ' + good_api_key})
        assert response.status_code == 200

    def test_get_client_simple(self, api_client, good_api_key):
        response = api_client.get(API_PREFIX + '/clients/simple',
                                  headers={'Authorization': 'Bearer ' + good_api_key})
        assert response.status_code == 200
