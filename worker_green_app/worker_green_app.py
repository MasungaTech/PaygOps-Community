from celery import Celery
from config import REDIS_HOST, REDIS_PORT, REDIS_DBS
from worker_app.error_handler import on_failure

redis_connection_string = f'redis://{REDIS_HOST}:{REDIS_PORT}'
worker_green_app = Celery('tasks', broker=redis_connection_string+'/'+REDIS_DBS.get('worker_green_app'), backend=redis_connection_string+'/'+REDIS_DBS.get('worker_green_app'))

# Configure gevent
worker_green_app.conf.update(
    worker_pool='gevent',
    task_annotations={'*': {'on_failure': on_failure}}
) # Absolutely required despite the warning
# Make the task being picked up even if the server crashed
worker_green_app.conf.broker_transport_options = {'visibility_timeout': 3600 * 12}
