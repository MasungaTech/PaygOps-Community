from config import API_PREFIX

class TestOutgoingMessageRoute:

    def test_send_message_no_recipient(self, api_client, good_api_key):
        response = api_client.post(API_PREFIX+'/outgoing_messages',
                                  headers={'Authorization': 'Bearer '+good_api_key},
                                  json={'body': 'This is a test but the number is missing'})
        assert response.status_code == 400

    def test_send_message_no_body(self, api_client, good_api_key):
        response = api_client.post(API_PREFIX+'/outgoing_messages',
                                  headers={'Authorization': 'Bearer '+good_api_key},
                                  json={'to_number': '+111222333444'})
        assert response.status_code == 400

    def test_send_message(self, api_client, good_api_key):
        response = api_client.post(API_PREFIX+'/outgoing_messages',
                                  headers={'Authorization': 'Bearer '+good_api_key},
                                  json={'to_number': '+111222333444',
                                        'body': 'This is a test message'})
        assert response.status_code == 201
