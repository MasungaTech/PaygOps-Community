from worker_green_app.worker_green_app import worker_green_app

# We import the tasks
# CRITICAL WARNING: BEFORE ADDING ANY TASK MAKE SURE THE TASK IS SUITABLE FOR USE WITH GEVENT
# THE TASK MUST HAVE LOW CPU USAGE AND LONG IO WAIT TIME AND NOT USE POSTGRES
from worker_green_app.tasks.delayed_api_post import delayed_post_request
from worker_green_app.tasks.delayed_api_get import delayed_get_request
from worker_green_app.tasks.green_healthcheck import green_healthcheck
