from worker_green_app.worker_green_app import worker_green_app
from shared.cache.redis_config import set_key


@worker_green_app.task()
def green_healthcheck():
    set_key('green_healthcheck', 'true', seconds_to_expiry=120)