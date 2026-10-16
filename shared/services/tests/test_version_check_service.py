import requests

from shared.services.version_check_service import VersionCheckService


def _enable(monkeypatch, version='oss-2.40.0'):
    monkeypatch.setattr('shared.services.version_check_service.config.ENABLE_ENTERPRISE_FEATURES', False)
    monkeypatch.setattr('shared.services.version_check_service.config.ENV_VAR', 'PROD')
    monkeypatch.setattr('shared.services.version_check_service.config.AUTOMATED_TESTING', False)
    monkeypatch.setattr('shared.services.version_check_service.config.VERSION', version)
    monkeypatch.delenv('DISABLE_VERSION_CHECK', raising=False)
    VersionCheckService.reset_cache()


def _stub_cache(monkeypatch, cached=VersionCheckService._MISS):
    monkeypatch.setattr(VersionCheckService, '_read_redis', classmethod(lambda cls: cached))
    monkeypatch.setattr(VersionCheckService, '_write_redis', classmethod(lambda cls, banner, ttl: None))


def test_parse_version_accepts_image_and_tag_forms():
    assert VersionCheckService.parse_version('oss-2.46.3') == (2, 46, 3)
    assert VersionCheckService.parse_version('2.46.3') == (2, 46, 3)
    assert VersionCheckService.parse_version('v2.46.3') == (2, 46, 3)


def test_parse_version_rejects_non_releases():
    assert VersionCheckService.parse_version('latest') is None
    assert VersionCheckService.parse_version('oss-NA') is None
    assert VersionCheckService.parse_version('local') is None
    assert VersionCheckService.parse_version('2.46') is None
    assert VersionCheckService.parse_version('2.46.3-rc1') is None
    assert VersionCheckService.parse_version('') is None


def test_latest_version_ignores_non_semver_tags():
    assert VersionCheckService.latest_version(['latest', '2.45.6', '2.46.3', 'nightly']) == (2, 46, 3)


def test_banner_when_registry_has_a_newer_release(monkeypatch):
    _enable(monkeypatch, 'oss-2.40.0')
    _stub_cache(monkeypatch)
    monkeypatch.setattr(
        VersionCheckService,
        '_fetch_tags',
        classmethod(lambda cls: ['2.39.0', '2.46.3', 'latest']),
    )

    assert VersionCheckService.get_banner() == {'current': '2.40.0', 'latest': '2.46.3'}


def test_no_banner_when_running_the_latest_release(monkeypatch):
    _enable(monkeypatch, 'oss-2.46.3')
    _stub_cache(monkeypatch)
    monkeypatch.setattr(VersionCheckService, '_fetch_tags', classmethod(lambda cls: ['2.46.3', 'latest']))

    assert VersionCheckService.get_banner() is None


def test_no_banner_when_running_a_newer_build_than_the_registry(monkeypatch):
    _enable(monkeypatch, 'oss-9.0.0')
    _stub_cache(monkeypatch)
    monkeypatch.setattr(VersionCheckService, '_fetch_tags', classmethod(lambda cls: ['2.46.3']))

    assert VersionCheckService.get_banner() is None


def test_no_banner_and_no_request_for_local_versions(monkeypatch):
    _enable(monkeypatch, 'local')

    def fail_fetch(cls):
        raise AssertionError('registry should not be contacted')

    monkeypatch.setattr(VersionCheckService, '_fetch_tags', classmethod(fail_fetch))

    assert VersionCheckService.get_banner() is None


def test_registry_failure_hides_the_banner_and_is_cached(monkeypatch):
    _enable(monkeypatch, 'oss-2.40.0')
    _stub_cache(monkeypatch)
    calls = {'n': 0}

    def fail_fetch(cls):
        calls['n'] += 1
        raise requests.ConnectionError('registry unavailable')

    monkeypatch.setattr(VersionCheckService, '_fetch_tags', classmethod(fail_fetch))

    assert VersionCheckService.get_banner() is None
    assert VersionCheckService.get_banner() is None
    assert calls['n'] == 1


def test_cached_registry_result_skips_another_fetch(monkeypatch):
    _enable(monkeypatch, 'oss-2.40.0')
    _stub_cache(monkeypatch, cached={'current': '2.40.0', 'latest': '2.46.3'})

    def fail_fetch(cls):
        raise AssertionError('registry should not be contacted')

    monkeypatch.setattr(VersionCheckService, '_fetch_tags', classmethod(fail_fetch))

    assert VersionCheckService.get_banner() == {'current': '2.40.0', 'latest': '2.46.3'}


def test_disabled_by_environment(monkeypatch):
    _enable(monkeypatch, 'oss-2.40.0')
    monkeypatch.setenv('DISABLE_VERSION_CHECK', '1')

    def fail_fetch(cls):
        raise AssertionError('registry should not be contacted')

    monkeypatch.setattr(VersionCheckService, '_fetch_tags', classmethod(fail_fetch))

    assert VersionCheckService.get_banner() is None


def test_fetch_tags_follows_registry_pagination(monkeypatch):
    token = type('Response', (), {})()
    token.raise_for_status = lambda: None
    token.json = lambda: {'token': 'abc'}

    first = type('Response', (), {})()
    first.raise_for_status = lambda: None
    first.json = lambda: {'tags': ['2.0.0']}
    first.headers = {
        'Link': '<https://ghcr.io/v2/masungatech/paygops-community/tags/list?n=1&last=2.0.0>; rel="next"'
    }

    second = type('Response', (), {})()
    second.raise_for_status = lambda: None
    second.json = lambda: {'tags': ['2.1.0', 'latest']}
    second.headers = {}

    def fake_get(url, **kwargs):
        if url.endswith('/token'):
            return token
        if 'last=' in url:
            return second
        return first

    monkeypatch.setattr('shared.services.version_check_service.requests.get', fake_get)

    assert VersionCheckService._fetch_tags() == ['2.0.0', '2.1.0', 'latest']
