import redis
from redis.exceptions import ConnectionError, TimeoutError, ResponseError
from config import REDIS_HOST, REDIS_PORT, AUTOMATED_TESTING, CACHING_ENABLED
import logging

logger = logging.getLogger(__name__)

# Create a connection pool with retry logic and proper timeouts
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    db=0,
    socket_connect_timeout=10,  # 10 seconds to establish connection
    socket_timeout=30,          # 30 seconds for operations
    retry_on_timeout=True,      # Retry on timeout
    health_check_interval=30,   # Check connection health every 30 seconds
    max_connections=100,        # Increased from 20 to handle actual usage
    socket_keepalive=True,      # Enable TCP keepalive
    socket_keepalive_options={}, # Use system defaults
)

R_SERVER = redis.Redis(connection_pool=redis_pool)

def _safe_redis_operation(operation, *args, **kwargs):
    """Wrapper to safely execute Redis operations with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = operation(*args, **kwargs)
            return result
        except (ConnectionError, TimeoutError) as e:
            if attempt == max_retries - 1:
                logger.error(f"Redis operation failed after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Redis connection error (attempt {attempt + 1}/{max_retries}): {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}")
            raise

def get_cache_key(key):
    if(not CACHING_ENABLED):
        return None
    return _safe_redis_operation(R_SERVER.get, key)

def set_cache_key(key, value, seconds_to_expiry=3600):
    if(not CACHING_ENABLED):
        return
    _safe_redis_operation(R_SERVER.set, key, value, ex=seconds_to_expiry)

def key_exists(key):
    if(not CACHING_ENABLED):
        return False
    return _safe_redis_operation(R_SERVER.exists, key)

def push_cache_value(list_key, array):
    if(not CACHING_ENABLED):
        return
    _safe_redis_operation(R_SERVER.lpush, list_key, *array)

def remove_cache_value(list_key, value):
    if(not CACHING_ENABLED):
        return
    _safe_redis_operation(R_SERVER.lrem, list_key, 0, value)

def get_cache_list(list_key):
    if(not CACHING_ENABLED):
        return None
    return _safe_redis_operation(R_SERVER.lrange, list_key, 0, -1)

def delete_cache_key(list_key):
    if(not CACHING_ENABLED):
        return
    _safe_redis_operation(R_SERVER.delete, list_key)

def delete_all_with_prefix(prefix):
    if(not CACHING_ENABLED):
        return
    keys = _safe_redis_operation(R_SERVER.keys, prefix+"*")
    if keys:
        for key in keys:
            _safe_redis_operation(R_SERVER.delete, key)

def delete_relevant_keys(cache_key_array):
    """
    Unpacks all keys that are found and runs them in one delete request which is much more optimal than separate 
    requests through iteration.
    :param cache_key_array: 
    :return: 
    """
    try:
        _safe_redis_operation(R_SERVER.delete, *cache_key_array)
    except ResponseError:
        print('This key does not exit yet.')

def get_list(list_key):
    return _safe_redis_operation(R_SERVER.lrange, list_key, 0, -1)

def push_list_value(list_key, array):
    _safe_redis_operation(R_SERVER.rpush, list_key, *array)

def delete_list_value(list_key, value):
    _safe_redis_operation(R_SERVER.lrem, list_key, 1, value)

def get_key(key):
    if AUTOMATED_TESTING:
        return {}
    return _safe_redis_operation(R_SERVER.get, key)

def get_keys(key):
    if AUTOMATED_TESTING:
        return {}
    keys = _safe_redis_operation(R_SERVER.keys, key)
    return keys if keys else []

def set_key(key, value, seconds_to_expiry=None):
    if AUTOMATED_TESTING:
        return
    _safe_redis_operation(R_SERVER.set, key, value, ex=seconds_to_expiry)
