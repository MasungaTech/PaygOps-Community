import sys
from shared.cache.redis_config import get_key


if __name__ == '__main__':
    if not get_key('beat_healthcheck') or not get_key('green_healthcheck'):
        sys.exit(1)
