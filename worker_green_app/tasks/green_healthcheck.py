import logging

from celery.signals import worker_ready

from shared.cache.redis_config import set_key
from worker_green_app.worker_green_app import worker_green_app

logger = logging.getLogger(__name__)

GREEN_HEALTHCHECK_TTL_SECONDS = 120
GREEN_HEALTHCHECK_INTERVAL_SECONDS = 30

_loop_started = False


def refresh_green_healthcheck():
    set_key('green_healthcheck', 'true', seconds_to_expiry=GREEN_HEALTHCHECK_TTL_SECONDS)


@worker_green_app.task()
def green_healthcheck():
    refresh_green_healthcheck()


def _green_healthcheck_loop():
    # Own greenlet, outside the task pool. A full pool of delayed_post_request
    # calls yields on HTTP, so this still runs and the healthcheck key stays
    # fresh while the webhook queue is backed up.
    import gevent

    logger.info('Green healthcheck loop started')
    while True:
        try:
            refresh_green_healthcheck()
        except Exception:
            logger.warning('Green healthcheck refresh failed', exc_info=True)
        gevent.sleep(GREEN_HEALTHCHECK_INTERVAL_SECONDS)


@worker_ready.connect
def start_green_healthcheck_loop(sender=None, **kwargs):
    global _loop_started
    if getattr(sender, 'app', None) is not worker_green_app or _loop_started:
        return
    import gevent

    _loop_started = True
    gevent.spawn(_green_healthcheck_loop)
