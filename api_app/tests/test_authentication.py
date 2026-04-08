import json
from config import API_PREFIX, BASE_PLATFORM_NAME


def test_HelloRoute(api_client, good_api_key):
    response = api_client.get(API_PREFIX)
    assert response.status_code == 200, response.json
    assert json.loads(response.data.decode('utf8'))['api_name'] == BASE_PLATFORM_NAME


def test_SecureRoute_unauthentified(api_client):
    response = api_client.get(API_PREFIX+'/test_route')
    assert response.status_code == 401


def test_SecureRoute_badapikey(api_client):
    response = api_client.get(API_PREFIX+'/test_route', headers={'Authorization': 'Bearer ThisIsABadKey'})
    assert response.status_code == 401


def test_SecureRoute_expiredkey(api_client, expired_api_key):
    response = api_client.get(API_PREFIX+'/test_route', headers={'Authorization': 'Bearer '+expired_api_key})
    assert response.status_code == 401


def test_SecureRoute_goodkey(api_client, good_api_key):
    # This key expires in 2023
    response = api_client.get(API_PREFIX+'/test_route', headers={'Authorization': 'Bearer '+good_api_key})
    assert response.status_code == 200


def test_SecureRoute_goodkey_badpermisison(api_client, api_key_bad_permissions):
    # This key expires in 2023
    response = api_client.get(API_PREFIX+'/test_route', headers={'Authorization': 'Bearer '+api_key_bad_permissions})
    assert response.status_code == 403
