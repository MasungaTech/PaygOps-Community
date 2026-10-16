import config
import json
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt
from datetime import datetime, timedelta
from shared.api_helpers.client_helpers.json_serialization_helpers import serialize_data_to_json


goodkey = generate_jwt(2, ['TestPostPermission'], 'Solaris Offgrid', config.api_secret,
                 expiration_time=datetime.now() + timedelta(days=1))


def test_PostRoute_no_json(api_client):
    response = api_client.post(config.API_PREFIX+'/test_route', data='',
                           headers={'Authorization': 'Bearer '+goodkey, 'content-type': 'application/json'})
    assert response.status_code == 415


def test_PostRoute_bad_schema(api_client):
    response = api_client.post(config.API_PREFIX+'/test_route', data=serialize_data_to_json({'test_name': 'basic_post_test'}),
                           headers={'Authorization': 'Bearer '+goodkey, 'content-type': 'application/json'})
    assert response.status_code == 400


def test_PostRoute_good_schema(api_client):
    response = api_client.post(config.API_PREFIX+'/test_route', data=serialize_data_to_json({'test_name': 'basic_post_test',
                                                                                  'test_datetime': datetime.now(),
                                                                                   'test_number': 3}),
                           headers={'Authorization': 'Bearer ' + goodkey, 'content-type': 'application/json'})
    assert response.status_code == 200


def test_PostRoute_good_schema_without_optional(api_client):
    response = api_client.post(config.API_PREFIX+'/test_route', data=serialize_data_to_json({'test_name': 'basic_post_test',
                                                           'test_number': 3}),
                           headers={'Authorization': 'Bearer ' + goodkey, 'content-type': 'application/json'})
    assert response.status_code == 200


def test_PostRoute_datetime_conversion(api_client):
    response = api_client.post(config.API_PREFIX+'/test_route', data=serialize_data_to_json({'test_name': 'test_datetime',
                                                                                  'test_datetime': datetime.fromtimestamp(1515418430),
                                                                                   'test_number': 3}),
                           headers={'Authorization': 'Bearer ' + goodkey, 'content-type': 'application/json'})
    assert response.status_code == 200
    assert json.loads(response.data.decode('utf8'))['converted_datetime'] == "01/08/2018"
