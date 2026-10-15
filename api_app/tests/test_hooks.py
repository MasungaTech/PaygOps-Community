from shared.api_helpers.hook_helpers.hook_service import WebhookService
from mock import patch
from config import API_PREFIX
from pony import orm


class TestHooks:
    def test_add_hook_invalid_event(self, api_client, good_api_key):
        response = api_client.post(API_PREFIX+'/hook_subscription/create',
                                  headers={'Authorization': 'Bearer '+good_api_key},
                                  json={'event': 'invalid_event',
                                        'target_url': "https://invalid.com"})
        assert response.status_code == 400


    def test_add_hook_valid_event(self, api_client, good_api_key):
        response = api_client.post(API_PREFIX+'/hook_subscription/create',
                                    headers={'Authorization': 'Bearer '+good_api_key},
                                    json={'event': 'test_event',
                                            'target_url': "https://test-url-1.com"})
        assert response.status_code == 201


    def test_that_hook_url_exist(self, api_client, good_api_key):
        with orm.db_session:
            orm.flush()
            hook_urls = [h.target_url for h in WebhookService.get_hooks_for_event('test_event')]
        assert "https://test-url-1.com" in str(hook_urls)


    def test_delete_hook_invalid_url(self, api_client, good_api_key):
        response = api_client.post(API_PREFIX+'/hook_subscription/delete',
                                  headers={'Authorization': 'Bearer '+good_api_key},
                                  json={'target_url': "https://doesnotexist.com"})
        assert response.status_code == 404

    def test_delete_hook_valid_url(self, api_client, good_api_key):
        response = api_client.post(API_PREFIX+'/hook_subscription/delete',
                                  headers={'Authorization': 'Bearer '+good_api_key},
                                  json={'target_url': "https://test-url-1.com"})
        assert response.status_code == 200


    def test_that_hook_url_does_not_exist(self, api_client, good_api_key):
        with orm.db_session:
            orm.flush()
            hook_urls = [h.target_url for h in WebhookService.get_hooks_for_event('test_event')]
        assert "https://test-url-1.com" not in hook_urls

