from config import API_PREFIX


class BaseAPITest:
    BASE_URL = ''
    SAMPLE_DATA = {}
    EDIT_DATA = {}
    RESPONSE_DATA = {}
    ADD_NEW_ID = False

    def setup_class(self):
        pass

    @classmethod
    def _post_data(cls, route, data, api_client, admin_api_key):
        response = api_client.post(API_PREFIX+route,
                                   json=data,
                                   headers={'Authorization': 'Bearer ' + admin_api_key})
        print(response.json)
        return response

    @classmethod
    def _get_data(cls, route, api_client, admin_api_key):
        response = api_client.get(API_PREFIX + route, headers={'Authorization': 'Bearer ' + admin_api_key})
        return response

    @classmethod
    def _check_if_data_in_dict_match(cls, dict1, dict2):
        for key, dict1_value in dict1.items():
            if isinstance(dict1_value, list):
                assert sorted(dict2.get(key, [])) == sorted(dict1_value)
            else:
                print(str(key)+' ('+str(dict2.get(key))+') '+str(dict1_value))
                print([dict1, dict2])
                assert dict2.get(key) == dict1_value, f"Value for {key} received is {dict1_value} instead of {dict2.get(key)}"

    def test_add(self, api_client, admin_api_key):
        response = self._post_data(self.BASE_URL, self.SAMPLE_DATA, api_client, admin_api_key)
        assert response.status_code == 201
        id = response.json.get('id')
        self.SAMPLE_DATA['id'] = id
        if self.ADD_NEW_ID:
            self.SAMPLE_DATA['entity_id'] = response.json.get('entity_id')
        self._check_if_data_in_dict_match(response.json, {**self.SAMPLE_DATA, **self.RESPONSE_DATA})

    def test_list(self, api_client, admin_api_key):
        response = self._get_data(self.BASE_URL, api_client, admin_api_key)
        assert response.status_code == 200

    def test_get(self, api_client, admin_api_key):
        response = self._get_data(self.BASE_URL+'/'+str(self.SAMPLE_DATA['id']), api_client, admin_api_key)
        assert response.status_code == 200, response.json
        self._check_if_data_in_dict_match(response.json, {**self.SAMPLE_DATA, **self.RESPONSE_DATA})

    def test_edit(self, api_client, admin_api_key):
        response = self._post_data(self.BASE_URL+'/'+str(self.SAMPLE_DATA['id']), self.EDIT_DATA, api_client, admin_api_key)
        assert response.status_code == 200
        self.SAMPLE_DATA.update(self.EDIT_DATA)
        self._check_if_data_in_dict_match(response.json, {**self.SAMPLE_DATA, **self.RESPONSE_DATA})
