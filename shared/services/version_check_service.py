import json
import logging
import os
import re
import threading
import time

import requests

import config
from shared.cache.redis_config import get_cache_key, set_cache_key

logger = logging.getLogger(__name__)


class VersionCheckService:
    """Compare the running Community Edition image with tags published on GHCR."""

    REGISTRY = 'ghcr.io'
    REPOSITORY = 'masungatech/paygops-community'
    CACHE_KEY = 'oss_published_version_check'
    SUCCESS_TTL = 6 * 60 * 60
    FAILURE_TTL = 15 * 60
    MEMORY_TTL = 60 * 60
    REQUEST_TIMEOUT = 5
    PAGE_SIZE = 100
    MAX_TAG_PAGES = 20

    _SEMVER = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')
    _NEXT_LINK = re.compile(r'<([^>]+)>;\s*rel="next"')
    _MISS = object()
    _memory_banner = None
    _memory_expires = 0.0
    _lock = threading.Lock()

    @classmethod
    def get_banner(cls):
        try:
            return cls._get_banner()
        except Exception as error:
            logger.warning('Could not check PaygOps Community version: %s', error)
            return None

    @classmethod
    def reset_cache(cls):
        cls._memory_banner = None
        cls._memory_expires = 0.0

    @classmethod
    def parse_version(cls, value):
        if not value:
            return None
        text = str(value).strip()
        if text.startswith('oss-'):
            text = text[4:]
        if text.startswith('v'):
            text = text[1:]
        match = cls._SEMVER.match(text)
        if not match:
            return None
        return tuple(int(part) for part in match.groups())

    @classmethod
    def format_version(cls, version):
        return '.'.join(str(part) for part in version)

    @classmethod
    def latest_version(cls, tags):
        versions = [cls.parse_version(tag) for tag in tags]
        versions = [version for version in versions if version]
        if not versions:
            return None
        return max(versions)

    @classmethod
    def _enabled(cls):
        if config.ENABLE_ENTERPRISE_FEATURES or config.ENV_VAR == 'TEST' or config.AUTOMATED_TESTING:
            return False
        return os.getenv('DISABLE_VERSION_CHECK', '') not in ['1', 'true', 'True']

    @classmethod
    def _get_banner(cls):
        if not cls._enabled():
            return None
        current = cls.parse_version(config.VERSION)
        if current is None:
            return None
        if cls._memory_expires > time.monotonic():
            return cls._memory_banner
        if not cls._lock.acquire(blocking=False):
            return cls._memory_banner
        try:
            if cls._memory_expires > time.monotonic():
                return cls._memory_banner
            cached = cls._read_redis()
            if cached is not cls._MISS:
                cls._remember(cached, cls.MEMORY_TTL)
                return cached
            banner, ttl = cls._check(current)
            cls._write_redis(banner, ttl)
            cls._remember(banner, ttl)
            return banner
        finally:
            cls._lock.release()

    @classmethod
    def _remember(cls, banner, ttl):
        cls._memory_banner = banner
        cls._memory_expires = time.monotonic() + ttl

    @classmethod
    def _check(cls, current):
        try:
            tags = cls._fetch_tags()
        except Exception as error:
            logger.warning('Could not check PaygOps Community version: %s', error)
            return None, cls.FAILURE_TTL
        latest = cls.latest_version(tags)
        if latest is None or current >= latest:
            return None, cls.SUCCESS_TTL
        return {
            'current': cls.format_version(current),
            'latest': cls.format_version(latest),
        }, cls.SUCCESS_TTL

    @classmethod
    def _fetch_tags(cls):
        token_response = requests.get(
            f'https://{cls.REGISTRY}/token',
            params={'service': cls.REGISTRY, 'scope': f'repository:{cls.REPOSITORY}:pull'},
            timeout=cls.REQUEST_TIMEOUT,
        )
        token_response.raise_for_status()
        token = token_response.json().get('token') or token_response.json().get('access_token')
        if not token:
            raise ValueError('Container registry did not return a token')

        tags = []
        url = f'https://{cls.REGISTRY}/v2/{cls.REPOSITORY}/tags/list?n={cls.PAGE_SIZE}'
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        for _ in range(cls.MAX_TAG_PAGES):
            response = requests.get(url, headers=headers, timeout=cls.REQUEST_TIMEOUT)
            response.raise_for_status()
            tags.extend(response.json().get('tags') or [])
            url = cls._next_page_url(response.headers.get('Link'))
            if not url:
                break
        return tags

    @classmethod
    def _next_page_url(cls, link_header):
        if not link_header:
            return None
        for part in link_header.split(','):
            match = cls._NEXT_LINK.search(part)
            if match:
                return match.group(1)
        return None

    @classmethod
    def _cache_key(cls):
        current = cls.parse_version(config.VERSION)
        version = cls.format_version(current) if current else 'unknown'
        return f'{cls.CACHE_KEY}:{version}'

    @classmethod
    def _read_redis(cls):
        try:
            raw = get_cache_key(cls._cache_key())
        except Exception:
            return cls._MISS
        if raw is None:
            return cls._MISS
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return cls._MISS
        if not isinstance(data, dict) or 'banner' not in data:
            return cls._MISS
        return data['banner']

    @classmethod
    def _write_redis(cls, banner, ttl):
        try:
            set_cache_key(cls._cache_key(), json.dumps({'banner': banner}), seconds_to_expiry=ttl)
        except Exception:
            logger.warning('Could not cache PaygOps Community version check', exc_info=True)
