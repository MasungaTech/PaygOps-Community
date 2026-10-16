import pytest
from mock import patch
from werkzeug.exceptions import TooManyRequests

from shared.helpers.rate_limit_service import RateLimitService


@pytest.fixture
def mock_request():
    with patch.object(RateLimitService, '_request_ip', return_value='203.0.113.10'):
        yield


class TestRateLimitService:

    @patch('shared.helpers.rate_limit_service.ENV_VAR', 'PROD')
    @patch('shared.helpers.rate_limit_service.AUTOMATED_TESTING', False)
    @patch('shared.helpers.rate_limit_service._safe_redis_operation')
    def test_allows_requests_under_limit(self, mock_redis_op, mock_request):
        mock_redis_op.return_value = 1
        RateLimitService.check_api_key_request_ip()

    @patch('shared.helpers.rate_limit_service.ENV_VAR', 'PROD')
    @patch('shared.helpers.rate_limit_service.AUTOMATED_TESTING', False)
    @patch('shared.helpers.rate_limit_service.API_KEY_RATE_LIMIT_IP_MAX', 10)
    @patch('shared.helpers.rate_limit_service._safe_redis_operation')
    def test_blocks_requests_over_limit(self, mock_redis_op, mock_request):
        mock_redis_op.return_value = 11
        with pytest.raises(TooManyRequests):
            RateLimitService.check_api_key_request_ip()

    @patch('shared.helpers.rate_limit_service.ENV_VAR', 'TEST')
    @patch('shared.helpers.rate_limit_service._safe_redis_operation')
    def test_skips_rate_limit_in_test_env(self, mock_redis_op, mock_request):
        RateLimitService.check_api_key_request_ip()
        mock_redis_op.assert_not_called()

    @patch('shared.helpers.rate_limit_service.ENV_VAR', 'PROD')
    @patch('shared.helpers.rate_limit_service.AUTOMATED_TESTING', False)
    @patch.dict('os.environ', {'SECONDARY_SERVER_IP': '203.0.113.10'})
    @patch('shared.helpers.rate_limit_service._safe_redis_operation')
    def test_exempts_split_server_ips(self, mock_redis_op, mock_request):
        RateLimitService.check_api_key_request_ip()
        mock_redis_op.assert_not_called()
