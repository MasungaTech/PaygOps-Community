import os

from flask import request
from werkzeug.exceptions import TooManyRequests

from config import (
    API_KEY_RATE_LIMIT_IP_MAX,
    API_KEY_RATE_LIMIT_IP_WINDOW,
    API_KEY_RATE_LIMIT_USER_MAX,
    API_KEY_RATE_LIMIT_USER_WINDOW,
    AUTOMATED_TESTING,
    ENV_VAR,
)
from shared.cache.redis_config import R_SERVER, _safe_redis_operation


class RateLimitService:

    @classmethod
    def _is_exempt(cls):
        if AUTOMATED_TESTING or ENV_VAR == 'TEST':
            return True
        request_ip = cls._request_ip()
        for env_var in ('SECONDARY_SERVER_IP', 'TERTIARY_SERVER_IP'):
            exempt_ip = os.getenv(env_var, '')
            if exempt_ip and request_ip == exempt_ip:
                return True
        return False

    @classmethod
    def _request_ip(cls):
        return str(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))

    @classmethod
    def _check_limit(cls, scope, identifier, max_requests, window_seconds):
        if cls._is_exempt():
            return
        key = f'rate_limit:{scope}:{identifier}'
        count = _safe_redis_operation(R_SERVER.incr, key)
        if count == 1:
            _safe_redis_operation(R_SERVER.expire, key, window_seconds)
        if count > max_requests:
            raise TooManyRequests('Too many requests. Please try again later.')

    @classmethod
    def check_api_key_request_ip(cls):
        cls._check_limit(
            'api_key_request_ip',
            cls._request_ip(),
            API_KEY_RATE_LIMIT_IP_MAX,
            API_KEY_RATE_LIMIT_IP_WINDOW,
        )

    @classmethod
    def check_api_key_request_username(cls, username):
        if not username:
            return
        cls._check_limit(
            'api_key_request_user',
            username.lower(),
            API_KEY_RATE_LIMIT_USER_MAX,
            API_KEY_RATE_LIMIT_USER_WINDOW,
        )
