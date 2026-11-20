"""
Device cloud credit_updates call made while PaygOps is answering an HTTP request
(e.g. POST /payments from the Gateway).

Incident 2026-10-29: the call used timeout=90 with up to 5 attempts while the
Gateway gives up after 30s and gunicorn kills the worker at 90s. These tests pin
the request-path budget below the Gateway timeout and make the credit update
uuid stable so a retry of the same payment cannot credit the device twice.
"""
from types import SimpleNamespace

import mock
import pytest
import requests
from flask import Flask

from payg_loan_system.devices.device_api.device_api_errors import DeviceAPIError
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIHelperV2
from shared.api_helpers.client_helpers.api_helper_object import APIHelper

GATEWAY_TIMEOUT_SECONDS = 30
MODULE = 'payg_loan_system.devices.device_api.device_api_request_service'


def _device(serial='OVES0001', device_type='OVS'):
    return SimpleNamespace(SerialNumber=serial, type=device_type)


def _repayment(*payment_ids):
    return SimpleNamespace(reconciled_payments=[
        SimpleNamespace(linked_payment=SimpleNamespace(id=pid) if pid is not None else None)
        for pid in payment_ids
    ])


def _credit_data(value='2026-11-10T12:00:00'):
    return {'credit_update_type': 'ADD_CREDIT', 'credit_value': value}


def _helper_with_mock_api():
    api = mock.Mock()
    api.post.return_value = {'token': '123 456 789', 'credit_value': '2026-11-10T12:00:00'}
    return DeviceAPIHelperV2(api, {}), api


class TestCreditUpdateTimeoutBudget:

    def test_request_path_uses_short_timeout_and_single_attempt(self):
        helper, api = _helper_with_mock_api()
        with Flask(__name__).test_request_context('/api/v1/payments', method='POST'), \
                mock.patch.object(DeviceAPIHelperV2, '_create_token_from_result'):
            helper.post_credit_update(_device(), _credit_data())
        kwargs = api.post.call_args.kwargs
        assert kwargs['max_attempts'] == DeviceAPIHelperV2.REQUEST_CREDIT_UPDATE_ATTEMPTS
        connect, read = kwargs['timeout']
        assert (connect, read) == DeviceAPIHelperV2.REQUEST_CREDIT_UPDATE_TIMEOUT
        assert connect == 3
        assert read == 22
        assert read < GATEWAY_TIMEOUT_SECONDS

    def test_background_path_keeps_long_timeout(self):
        # Celery tasks (fix_payment_processing, force_sync_devices) are not
        # raced by the Gateway, they keep the long timeout and default retries.
        helper, api = _helper_with_mock_api()
        with mock.patch.object(DeviceAPIHelperV2, '_create_token_from_result'):
            helper.post_credit_update(_device(), _credit_data())
        kwargs = api.post.call_args.kwargs
        assert kwargs['timeout'] == 90
        assert kwargs.get('max_attempts') is None

    def test_request_path_timeout_fails_fast_without_retry(self):
        api = APIHelper('https://device-cloud.invalid/api/v2/', 'jwt')
        helper = DeviceAPIHelperV2(api, {})
        with Flask(__name__).test_request_context('/api/v1/payments', method='POST'), \
                mock.patch.object(api.session, 'post', side_effect=requests.exceptions.ReadTimeout('slow')) as post, \
                mock.patch('shared.api_helpers.client_helpers.api_helper_object.time.sleep') as sleep:
            with pytest.raises(DeviceAPIError) as error:
                helper.post_credit_update(_device(), _credit_data())
        assert error.value.type == 'API_NETWORKING_ERROR'
        assert post.call_count == 1
        sleep.assert_not_called()
        connect, read = post.call_args.kwargs['timeout']
        assert (connect, read) == DeviceAPIHelperV2.REQUEST_CREDIT_UPDATE_TIMEOUT
        assert connect == 3
        assert read == 22
        assert read < GATEWAY_TIMEOUT_SECONDS


class TestAPIHelperMaxAttempts:

    def test_max_attempts_limits_retries_on_timeout(self):
        api = APIHelper('https://device-cloud.invalid/', 'jwt')
        with mock.patch.object(api.session, 'post', side_effect=requests.exceptions.ConnectTimeout('down')) as post, \
                mock.patch('shared.api_helpers.client_helpers.api_helper_object.time.sleep'):
            with pytest.raises(Exception):
                api.post('credit_updates/x', data={}, timeout=(5, 15), max_attempts=1)
        assert post.call_count == 1

    def test_default_attempts_unchanged(self):
        api = APIHelper('https://device-cloud.invalid/', 'jwt')
        with mock.patch.object(api.session, 'post', side_effect=requests.exceptions.ConnectTimeout('down')) as post, \
                mock.patch('shared.api_helpers.client_helpers.api_helper_object.time.sleep'):
            with pytest.raises(Exception):
                api.post('credit_updates/x', data={})
        assert post.call_count == APIHelper.MAX_RETRIES


class TestCreditUpdateUuid:

    @staticmethod
    def _posted_uuid(helper, api, device, data, repayments):
        with mock.patch.object(DeviceAPIHelperV2, '_create_token_from_result'):
            helper.post_credit_update(device, dict(data), repayments=repayments)
        url = api.post.call_args.args[0]
        assert url.startswith(DeviceAPIHelperV2.CREDIT_UPDATES)
        return url[len(DeviceAPIHelperV2.CREDIT_UPDATES):]

    def test_same_payment_retried_reuses_uuid(self):
        # Retrying the same payment (Gateway re-send, hourly fix_payment_processing)
        # after a timeout must hit the same device cloud credit update, which the
        # device cloud returns as-is instead of crediting the device again.
        helper, api = _helper_with_mock_api()
        first = self._posted_uuid(helper, api, _device(), _credit_data(), [_repayment(101)])
        # repayments are rebuilt after a rollback: new objects, same payment
        second = self._posted_uuid(helper, api, _device(), _credit_data(), [_repayment(101)])
        assert first == second

    def test_uuid_keeps_device_cloud_format(self):
        helper, api = _helper_with_mock_api()
        uuid = self._posted_uuid(helper, api, _device(), _credit_data(), [_repayment(101)])
        parts = uuid.split('-')
        assert [len(p) for p in parts] == [8, 8, 8]
        assert all(c in '0123456789abcdef' for c in ''.join(parts))

    @pytest.mark.parametrize('other_device, other_data, other_repayments', [
        (_device(serial='OVES0002'), _credit_data(), [_repayment(101)]),
        (_device(), _credit_data(value='2026-11-17T12:00:00'), [_repayment(101)]),
        (_device(), {'credit_update_type': 'DISABLE_PAYG', 'credit_value': '2026-11-10T12:00:00'}, [_repayment(101)]),
        (_device(), _credit_data(), [_repayment(102)]),
        (_device(), _credit_data(), [_repayment(101), _repayment(102)]),
    ])
    def test_different_credit_update_gets_different_uuid(self, other_device, other_data, other_repayments):
        helper, api = _helper_with_mock_api()
        base = self._posted_uuid(helper, api, _device(), _credit_data(), [_repayment(101)])
        other = self._posted_uuid(helper, api, other_device, other_data, other_repayments)
        assert base != other

    def test_without_payments_uuid_is_random(self):
        # Manual syncs and offline token generation are not tied to a payment:
        # keep a fresh uuid per call as before.
        helper, api = _helper_with_mock_api()
        first = self._posted_uuid(helper, api, _device(), _credit_data(), None)
        second = self._posted_uuid(helper, api, _device(), _credit_data(), None)
        third = self._posted_uuid(helper, api, _device(), _credit_data(), [_repayment(None)])
        assert len({first, second, third}) == 3
