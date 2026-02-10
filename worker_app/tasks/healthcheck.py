from worker_app.worker_app import worker_app
from shared.cache.redis_config import set_key


@worker_app.task(priority=0)
def beat_healthcheck():
    from worker_green_app.tasks.green_healthcheck import green_healthcheck
    set_key('beat_healthcheck', 'true', seconds_to_expiry=120)
    green_healthcheck.delay()
