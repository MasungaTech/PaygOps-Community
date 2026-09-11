import time
import requests
from datetime import datetime, timedelta

from shared.services.celery_queue_service import CeleryQueueService
from .json_serialization_helpers import serialize_data_to_json, deserialize_received_json
from .http_errors_helpers import check_request_status
from .api_exceptions import APINetworkingError
from worker_green_app.tasks.delayed_api_post import delayed_post_request
from worker_green_app.tasks.delayed_api_get import delayed_get_request
from shared.helpers.date_helper import formatDateStringToDate
from payg_loan_system.devices.model.device_mode import DeviceMode
import config


class APIHelper(object):

    USER_AGENT = 'PaygOps-DeviceAPI/1.0'
    MAX_RETRIES = 5
    RETRYABLE_STATUS_CODES = {429, 502, 503, 504, 520, 521, 522, 523, 524}

    def __init__(self, api_base_url, jwt_key=None, auth_base='Authorization', auth_prefix='Bearer'):
        self.api_base_url = api_base_url
        self.auth_base = auth_base
        self.auth_prefix = auth_prefix
        self.auth_headers = None
        self.token_refresh_function = None
        self.last_token_update = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.USER_AGENT})
        self.update_api_token(jwt_key)

    def clear_api_token(self):
        self.auth_headers = ''

    def update_api_token(self, new_api_token):
        if self.auth_base:
            self.auth_headers = {
                self.auth_base: self.auth_prefix + ' ' + new_api_token,
                'User-Agent': self.USER_AGENT,
            }
            self.auth_headers_json = {
                self.auth_base: self.auth_prefix + ' ' + new_api_token,
                'content-type': 'application/json',
                'User-Agent': self.USER_AGENT,
            }
            self.last_token_update = datetime.now()

    def attach_token_refresh_function(self, new_refresh_function):
        self.token_refresh_function = new_refresh_function

    def refresh_token_if_needed(self):
        if self.token_refresh_function is not None:
            self.token_refresh_function(self.last_token_update)

    @classmethod
    def _is_retryable_response(cls, response):
        if response.status_code in cls.RETRYABLE_STATUS_CODES:
            return True
        content_type = (response.headers.get('Content-Type') or '').lower()
        if 'application/json' in content_type:
            return False
        body = (response.text or '')[:4000].lower()
        return 'cloudflare' in body or 'cf-ray' in body or 'just a moment' in body

    def _request_with_retry(self, request_fn):
        delay = 1
        response = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = request_fn()
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
                if attempt == self.MAX_RETRIES:
                    print('Networking Error: ' + str(error))
                    raise APINetworkingError(str(error)) from error
                print(f'Transient networking error, retrying in {delay}s: {error}')
                time.sleep(delay)
                delay *= 2
                continue
            except Exception as error:
                print('Networking Error: ' + str(error))
                raise APINetworkingError(str(error)) from error
            if self._is_retryable_response(response) and attempt < self.MAX_RETRIES:
                print(f'Retryable HTTP {response.status_code} from device API, retrying in {delay}s')
                time.sleep(delay)
                delay *= 2
                continue
            check_request_status(response)
            return response
        check_request_status(response)
        return response

    def get(self, partial_url, params=None, expected_schema=None, timeout=30):
        self.refresh_token_if_needed()
        request_result = self._request_with_retry(lambda: self.session.get(
            self.api_base_url + partial_url, params=params,
            headers=self.auth_headers, verify=self._should_verify(),
            timeout=timeout
        ))
        return deserialize_received_json(request_result, expected_schema)

    def post(self, partial_url, params=None, data=None, expected_schema=None, timeout=30):
        self.refresh_token_if_needed()
        data_json = serialize_data_to_json(data)
        request_result = self._request_with_retry(lambda: self.session.post(
            self.api_base_url + partial_url, params=params,
            data=data_json, headers=self.auth_headers_json,
            verify=self._should_verify(), timeout=timeout
        ))
        return deserialize_received_json(request_result, expected_schema)

    def delayed_post(self, partial_url, params=None, data=None, log_error=True, custom_handlers=None, timeout=90):
        self.refresh_token_if_needed()
        data_json = serialize_data_to_json(data)
        delayed_post_request.delay(
            full_url=self.api_base_url+partial_url,
            params=params,
            data=data_json,
            auth_headers=self.auth_headers_json,
            log_error=log_error,
            custom_handlers=custom_handlers,
            timeout=timeout
        )

    def delayed_get(self, partial_url, params=None, log_error=True, custom_handlers=None, timeout=90):
        self.refresh_token_if_needed()
        delayed_get_request.delay(
            full_url=self.api_base_url+partial_url,
            params=params,
            auth_headers=self.auth_headers_json,
            log_error=log_error,    
            custom_handlers=custom_handlers,
            timeout=timeout
        )

    def put(self, partial_url, params=None, data=None, expected_schema=None, timeout=30):
        self.refresh_token_if_needed()
        data_json = serialize_data_to_json(data)
        request_result = self._request_with_retry(lambda: self.session.put(
            self.api_base_url + partial_url, params=params,
            data=data_json, headers=self.auth_headers_json,
            verify=self._should_verify(), timeout=timeout
        ))
        return deserialize_received_json(request_result, expected_schema)

    def delete(self, partial_url, params=None, data=None, expected_schema=None):
        self.refresh_token_if_needed()
        data_json = serialize_data_to_json(data)
        request_result = self._request_with_retry(lambda: self.session.delete(
            self.api_base_url + partial_url, params=params,
            data=data_json, headers=self.auth_headers_json,
            verify=self._should_verify()
        ))
        return deserialize_received_json(request_result, expected_schema)

    def _should_verify(self):
        if config.is_production_server():
            return True
        else:
            return False


class TestAPIHelper(APIHelper):

    def __init__(self, device_type, v='v1'):
        self.device_type = device_type
        self.v = v

    def put(self, partial_url, params=None, data=None, expected_schema=None):
        if self.v== 'v2':
            if 'credit_updates/' in partial_url:
                return FakeJsonResponse({
                    "uuid": partial_url.split("/", 1)[1],
                    "time": datetime.now(),
                    "commit_time": data['commit_time'],
                    "status": data['status'],
                    "status_details": [],
                    "credit_unit": "ABSOLUTE_TIME",
                    "credit_value": datetime.now() + timedelta(days=7),
                    "credit_update_type": "ADD_CREDIT",
                    "credit_update_mode": "AUTO",
                    "effective_credit_value": datetime.now() + timedelta(days=7),
                    "effective_credit_update_type": "ADD_CREDIT",
                    "effective_credit_update_mode": "TOKEN",
                    "token": "672 975 802",
                    "token_count": 2
                }).s(expected_schema)

    def delete(self, partial_url, params=None, data=None, expected_schema=None):
        pass

    def get_device_state(self, device):
        if device.Mode == DeviceMode.disabled:
            mode = 'DISABLE_PAYG'
        else:
            mode = 'SET_CREDIT'
        return {
            'credit_update_type': mode,
            'credit_value': device.ActiveUntil or datetime.now()
        }

    def post(self, partial_url, params=None, data=None, expected_schema=None, timeout=30):
        if self.v != 'v2':
            return FakeJsonResponse({
                "uuid": data['uuid'],
                "request_datetime": datetime.now(),
                "device": partial_url[8:-5],
                "sync_scope": data['sync_scope'],
                "sync_method": data['sync_scope'],
                "request_code": data['request_code'],
                "answer_code": "123 456 789",
                "success_status": 1,
                "status_message": "",
            }).s(expected_schema)
        else:
            if 'hooks/' in partial_url:
                return FakeJsonResponse({"success": True}).s(expected_schema)
            elif 'credit_updates/' in partial_url:
                return FakeJsonResponse({
                    "uuid": partial_url.split("/", 1)[1],
                    "device_serial_number": data['device_serial_number'],
                    "time": datetime.now(),
                    "commit_time": datetime.now(),
                    "status": data.get('status', "COMMITTED"),
                    "status_details": [],
                    "credit_unit": data.get('credit_unit', "ABSOLUTE_TIME"),
                    "credit_value": data['credit_value'],
                    "credit_update_type": data['credit_update_type'],
                    "credit_update_mode": "AUTO",
                    "effective_credit_value": data['credit_value'],
                    "effective_credit_update_type": "ADD_CREDIT",
                    "effective_credit_update_mode": "TOKEN",
                    "token": "123 456 789",
                    "token_count": 2
                }).s(expected_schema)
            else:
                credit_unit = data.get("credit_unit", "ABSOLUTE_TIME")
                if credit_unit != "ABSOLUTE_TIME":
                    credit_value = data.get("credit_value", 7)
                else:
                    credit_value = data.get("credit_value", datetime.now() + timedelta(days=int(7)))
                return FakeJsonResponse({
                    "uuid": partial_url.split('/')[1],
                    "device_serial_number": data['device_serial_number'],
                    "time": datetime.now(),
                    "commit_time": datetime.now(),
                    "status": "COMMITTED",
                    "status_details": [],
                    "credit_unit": credit_unit,
                    "credit_value": credit_value,
                    "credit_update_type": "ADD_CREDIT",
                    "credit_update_mode": "AUTO",
                    "effective_credit_value": credit_value,
                    "effective_credit_update_type": "ADD_CREDIT",
                    "effective_credit_update_mode": "TOKEN",
                    "token": "123 456 789",
                    "token_count": 2
                }).s(expected_schema)

    def get(self, partial_url, params=None, expected_schema=None, timeout=30):
        if self.v == 'v1':
            if partial_url == 'devices':
                return [params.get('code', 9120029) if params else 9120029]
            elif partial_url[-5:] == '/sync':
                return FakeJsonResponse([{
                    "id": 1,
                    "uuid": "first-activation-token-"+self.device_type+partial_url[8:-5],
                    "request_datetime": datetime.now().isoformat(),
                    "device": partial_url[8:-5],
                    "sync_scope": 1,
                    "sync_method": 1,
                    "request_code": "",
                    "answer_code": "672 975 802",
                    "success_status": 1,
                    "status_message": "",
                }]).s(expected_schema)
            else:
                return FakeJsonResponse({
                    "serialNumber": partial_url[8:],
                    "client_id": 123,
                    "expiration_datetime": datetime.now().isoformat(),
                    "payg_mode": 1
                }).s(expected_schema)
        else:
            if partial_url == 'devices':
                return [params.get('code', 9120029) if params else 9120029]
            if partial_url == 'credit_updates':
                return FakeJsonResponse([{
                    "uuid": "first-activation-token-"+self.device_type+params['device_serial_number'],
                    "device_serial_number": params['device_serial_number'],
                    "time": datetime.now(),
                    "commit_time": datetime.now(),
                    "status": "COMMITETD",
                    "status_details": [],
                    "credit_unit": "ABSOLUTE_TIME",
                    "credit_value": datetime.now() + timedelta(days=7),
                    "credit_update_type": "ADD_CREDIT",
                    "credit_update_mode": "AUTO",
                    "effective_credit_value": datetime.now() + timedelta(days=7),
                    "effective_credit_update_type": "ADD_CREDIT",
                    "effective_credit_update_mode": "TOKEN",
                    "token": "672 975 802",
                    "token_count": 2
                }]).s(expected_schema)
            if partial_url.endswith('metrics'):
                return FakeJsonResponse([{
                    "uuid": "123",
                    "name": "Power consumption",
                    "unit": "W",
                    "format": 'Numeric', # either 'Numeric', 'Alert', 'GPS', 'String'
                    "extra_data": {}  
                },
                {
                    "uuid": "456",
                    "name": "Water consumption",
                    "unit": "LITRES",
                    "format": 'Numeric', # either 'Numeric', 'Alert', 'GPS', 'String'
                    "extra_data": {}
                },
                {
                    "uuid": "789",
                    "name": "Gps Coordinates",
                    "unit": "N/A",
                    "format": 'GPS', # either 'Numeric', 'Alert', 'GPS', 'String'
                    "extra_data": {}
                },
                {
                    "uuid": "000",
                    "name": "String Test",
                    "unit": "N/A",
                    "format": 'String', # either 'Numeric', 'Alert', 'GPS', 'String'
                    "extra_data": {}
                }]).s(expected_schema)
            if 'metrics' in partial_url:
                last_metric_date = formatDateStringToDate(params['from'])
                uuid = partial_url.split('metrics/', 1)[1]
                if uuid == "123":
                    response = [
                            {
                                "time": datetime.now() - timedelta(weeks=7),
                                "value": 1200,
                                "secondary_value": None,
                                "string": ""
                            },
                            {
                                "time": datetime.now() - timedelta(weeks=6),
                                "value": 500,
                                "secondary_value": None,
                                "string": ""
                            },
                            {
                                "time": datetime.now() - timedelta(weeks=4),
                                "value": 3000,
                                "secondary_value": None,
                                "string": ""
                            },
                            {
                                "time": datetime.now() - timedelta(weeks=2),
                                "value": 5500,
                                "secondary_value": None,
                                "string": ""
                            },
                            {
                                "time": datetime.now() - timedelta(days=7),
                                "value": 200,
                                "secondary_value": None,
                                "string": ""
                            },
                            {
                                "time": datetime.now() - timedelta(days=5),
                                "value": 100,
                                "secondary_value": None,
                                "string": ""
                            },
                            {
                                "time": datetime.now() - timedelta(days=3),
                                "value": 1200,
                                "secondary_value": None,
                                "string": ""
                            },
                            {
                                "time": datetime.now(),
                                "value": 1800,
                                "secondary_value": None,
                                "string": ""
                            }
                        ]
                elif uuid == "456":
                    response = [
                        {
                            "time": datetime.now() - timedelta(weeks=9),
                            "value": 800,
                            "secondary_value": None,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(weeks=8),
                            "value": 1000,
                            "secondary_value": None,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(weeks=6),
                            "value": 1500,
                            "secondary_value": None,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(weeks=2),
                            "value": 900,
                            "secondary_value": None,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(days=5),
                            "value": 5000,
                            "secondary_value": None,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(days=3),
                            "value": 2250,
                            "secondary_value": None,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(days=1),
                            "value": 1900,
                            "secondary_value": None,
                            "string": ""
                        },
                        {
                            "time": datetime.now(),
                            "value": 400,
                            "secondary_value": None,
                            "string": ""
                        }
                    ]
                elif uuid == "789":
                    response = [
                        {
                            "time": datetime.now() - timedelta(weeks=9),
                            "value": -106.52564,
                            "secondary_value": 16.56554,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(weeks=8),
                            "value": -68.66165,
                            "secondary_value": -25.57633,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(weeks=6),
                            "value": -35.99738,
                            "secondary_value": 25.34982,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(weeks=2),
                            "value": -56.07076,
                            "secondary_value": -15.40089,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(days=5),
                            "value": 177.26614,
                            "secondary_value": -29.52743,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(days=3),
                            "value": -53.00736,
                            "secondary_value": 7.09676,
                            "string": ""
                        },
                        {
                            "time": datetime.now() - timedelta(days=1),
                            "value": -157.31866,
                            "secondary_value": -14.85969,
                            "string": ""
                        },
                        {
                            "time": datetime.now(),
                            "value": 28.89821,
                            "secondary_value": 25.49960,
                            "string": ""
                        }
                    ]
                elif uuid == "000":
                    response = [
                        {
                            "time": datetime.now() - timedelta(days=1),
                            "value": None,
                            "secondary_value": None,
                            "string": "Yes"
                        },
                        {
                            "time": datetime.now(),
                            "value": None,
                            "secondary_value": None,
                            "string": "No"
                        }
                    ]
                metrics = [r for r in response if r["time"] > last_metric_date]
                return FakeJsonResponse(metrics).s(expected_schema)
            if 'devices' in partial_url:
                data = {
                    "model": "Default",
                    "payg_mode": 1,
                    "credit_unit": "ABSOLUTE_TIME",
                    "credit_value": datetime.now() + timedelta(days=7),
                    "effective_credit_value": datetime.now() + timedelta(days=7),
                    "supported_credit_units": ["ABSOLUTE_TIME", "DAYS", "WATTS", "LITRES", "GPS"],
                    "supported_credit_update_types": ["ADD_CREDIT", "SET_CREDIT", "DISABLE_PAYG"],
                    "supported_credit_update_modes": ["TOKEN", "AUTO"],
                    "pending_token_limit": 5
                }
                if not '/' in partial_url:
                    data = [data]
                return FakeJsonResponse(data).s(expected_schema)
            if partial_url == 'support':
                return FakeJsonResponse({
                    "supported_credit_units": {"ABSOLUTE_TIME": "Expiration Date", "DAYS": "Days", "WATTS": "Watts", "LITRES": "Litres"}
                }).s(expected_schema)
                


class FakeJsonResponse():

    def __init__(self, json):
        self.text = serialize_data_to_json(json)

    def s(self, schema):
        return deserialize_received_json(self, schema)
