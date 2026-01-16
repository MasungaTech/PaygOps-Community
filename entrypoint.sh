#!/usr/bin/env bash

echo "Starting PaygOps OSS"

# Create pdbpp config
if [[ "$ENV_VAR" == *"DEV"* ]]; then
cat > ~/.pdbrc.py <<EOF
import pdb
class Config(pdb.DefaultConfig):
    sticky_by_default = True
    truncate_long_lines = False
EOF
fi


# Necessary to avoid large delays in outputs
export PYTHONUNBUFFERED=TRUE

# Constants
if [[ -z "$TIMEOUT" ]]; then
    TIMEOUT=90
fi
MOBILE_SYNC_TIMEOUT=240
LOG_DIR=./data/logs

# We do that so that we can enable reloading in development
# If we don't want to reload, we cant preload before forking worker for faster uptime
RELOAD_COMMAND="--preload"
if [[ ! -z "$RELOAD_PYTHON" ]]; then
    if [[ "$RELOAD_PYTHON" == true ]]; then
        RELOAD_COMMAND="--reload"
    fi
fi


LOGGER_COMMAND="--log-level=debug --log-file=- --logger-class shared.logger.CustomLogger"
MAX_REQUEST_COMMAND="--max-requests 200 --max-requests-jitter 100"
MAX_REQUEST_COMMAND_MOBILE="--max-requests 50 --max-requests-jitter 25"
SHARED_GUNICORN_COMMAND="$RELOAD_COMMAND $LOGGER_COMMAND "

# We do that to be able to set a default scale when not specified
if [[ -z "$DEFAULT_SCALE" ]]; then
    DEFAULT_SCALE=2
fi
if [[ -z "$GLOBAL_SCALE" ]]; then
    GLOBAL_SCALE=$DEFAULT_SCALE
    if (( GLOBAL_SCALE < 2 )); then 
        GLOBAL_SCALE=2
    fi
    echo "Scale: $GLOBAL_SCALE"
fi
if [[ -n "$START_METABASE" ]]; then
    # If we have a smallish server, we need to remove some scale 
    # to save the ~800MB of RAM of Metabase
    # On bigger server there's enough RAM buffer that it's not needed
    if (( GLOBAL_SCALE > 3 && GLOBAL_SCALE < 8 )); then 
        GLOBAL_SCALE=$((GLOBAL_SCALE-2))
        echo "Metabase Adjusted Scale: $GLOBAL_SCALE"
    fi
fi
# We adapt the scale of services based on server configuration
if [[ -z "$SPLIT_SERVER_MODE" || "$SPLIT_SERVER_MODE" == "STANDARD" || "$SPLIT_SERVER_MODE" == "MAIN" ]]; then
    SERVICES_SCALE=$((GLOBAL_SCALE)) 
    # If the main server has the PG_SCALE_FACTOR > 1 
    # we decrease the number of services to leave RAM for the DB
    if [[ -n "$PG_SCALE_FACTOR" ]]; then
        if [["$SPLIT_SERVER_MODE" == "MAIN" && "$PG_SCALE_FACTOR" -gt 1 && "$GLOBAL_SCALE" -gt 15 ]]; then
            SERVICES_SCALE=$((GLOBAL_SCALE/4))
            echo "Main Server Adjusted Services Scale: $SERVICES_SCALE"
        fi
    fi
fi
if [[ "$SPLIT_SERVER_MODE" == "SECONDARY" ]]; then
    # If the server is secondary we double all services
    # This allows to use 100% of all CPUs (whereas in regular mode we keep some for the DB)
    SERVICES_SCALE=$((GLOBAL_SCALE*2))
    echo "Secondary Server Adjusted Services Scale: $SERVICES_SCALE"
fi
if [[ -z "$WEB_SCALE" ]]; then
    WEB_SCALE=$((SERVICES_SCALE))
fi
if [[ -z "$MOBILE_SYNC_SCALE" ]]; then
    # If below 4, we reduce by 1 to save RAM
    # Mobile request are not that frequent so it's ok
    MOBILE_SYNC_SCALE=$((SERVICES_SCALE-1))
    if (( SERVICES_SCALE > 4 )); then 
        MOBILE_SYNC_SCALE=$((SERVICES_SCALE))
    fi
fi
if [[ -z "$API_SCALE" ]]; then
    # If below 3, we reduce by 1 to save RAM
    # API requests are fast so it's ok
    API_SCALE=$((SERVICES_SCALE-1))
    if (( SERVICES_SCALE > 4 )); then 
        API_SCALE=$((SERVICES_SCALE))
    fi
    if [[ "$SPLIT_SERVER_MODE" == "SECONDARY" ]]; then
        # For larger servers in secondary mode, we put more API
        # as it's likely to be most limiting
        API_SCALE=$((SERVICES_SCALE*2))
    fi
fi
if [[ -z "$WORKER_SCALE" ]]; then
    # Minimum worker scale is 2 to allow essential tasks and slightly longer ones
    # We don't need many workers anymore since they don't stay blocked on external requests
    WORKER_SCALE=2
    if (( GLOBAL_SCALE > 3 )); then 
        WORKER_SCALE=4
    fi
    if (( GLOBAL_SCALE > 15 )); then 
        WORKER_SCALE=$((GLOBAL_SCALE/4))
    fi
fi
if [[ -z "$WORKER_GREEN_SCALE" ]]; then
    WORKER_GREEN_SCALE=$((GLOBAL_SCALE*100))
fi
if [[ -z "$HEAVY_WORKER_SCALE" ]]; then
    HEAVY_WORKER_SCALE=1
fi
if [ "$1" = "runtime_setup" ]; then
    rm /setup_data/ready
    if [[ -z "$SPLIT_SERVER_MODE" || "$SPLIT_SERVER_MODE" == "STANDARD" || "$SPLIT_SERVER_MODE" == "MAIN" ]]; then
        until pg_isready -q -h postgres > /dev/null 2>&1; do
            echo "Waiting for db..."
            sleep 1
        done
    fi
    rm -rf /temp/prometheus_multiproc/setup
    mkdir -p /temp/prometheus_multiproc/setup
    export PROMETHEUS_MULTIPROC_DIR=/temp/prometheus_multiproc/setup
    python3 /crm/shared/migrations/commands/create_db.py
    export INSTALL_MODE=1
    python3 /crm/shared/migrations/commands/init_db.py
    export INSTALL_MODE=0
    export MIGRATE_MODE=1
    python3 /crm/update.py
    export MIGRATE_MODE=0
    echo "Ready to start!"
    touch /setup_data/ready
    exit 0
elif [[ "$1" = "start_web_app" ]]; then
    echo "Starting Web App"
    sleep 3;
    while [ ! -f /setup_data/ready ]; do sleep 1; done
    rm -rf /temp/prometheus_multiproc/web
    mkdir -p /temp/prometheus_multiproc/web
    export PROMETHEUS_MULTIPROC_DIR=/temp/prometheus_multiproc/web
    gunicorn web_app:app -c /crm/shared/monitoring/gunicorn_conf.py -w $WEB_SCALE -t $TIMEOUT --limit-request-line 8190 $SHARED_GUNICORN_COMMAND $MAX_REQUEST_COMMAND -b 0.0.0.0:8000
    exit $?
elif [[ "$1" = "start_api_app" ]]; then
    echo "Starting API App"
    sleep 3;
    rm -rf /temp/prometheus_multiproc/api
    mkdir -p /temp/prometheus_multiproc/api
    export PROMETHEUS_MULTIPROC_DIR=/temp/prometheus_multiproc/api
    while [ ! -f /setup_data/ready ]; do sleep 1; done
    gunicorn api_app:api_app -c /crm/shared/monitoring/gunicorn_conf.py -w $API_SCALE -t $TIMEOUT $SHARED_GUNICORN_COMMAND $MAX_REQUEST_COMMAND -b 0.0.0.0:6789
    exit $?
elif [[ "$1" = "start_worker" ]]; then
    echo "Starting Worker App"
    sleep 3;
    while [ ! -f /setup_data/ready ]; do sleep 1; done
    celery -A worker_app.celery_worker.worker_app worker --autoscale=$WORKER_SCALE,1 -E -l info --max-tasks-per-child=250
    exit $?
elif [[ "$1" = "start_heavy_worker" ]]; then
    echo "Starting Heavy Worker App"
    sleep 3;
    while [ ! -f /setup_data/ready ]; do sleep 1; done
    celery -A worker_app.celery_worker.worker_app worker --autoscale=$HEAVY_WORKER_SCALE,1 --max-tasks-per-child=1 -E -l info -Q heavy --concurrency=1 -- worker.prefetch_multiplier=1
    exit $?
elif [[ "$1" = "start_green_worker" ]]; then
    echo "Starting Green Worker App with scale $WORKER_GREEN_SCALE"
    sleep 3;
    while [ ! -f /setup_data/ready ]; do sleep 1; done
    celery -A worker_green_app.celery_worker_green worker -E -l info -P gevent -c $WORKER_GREEN_SCALE
    exit $?
elif [[ "$1" = "start_beat" ]]; then
    echo "Starting Beat App"
    sleep 3;
    while [ ! -f /setup_data/ready ]; do sleep 1; done
    celery -A worker_app.celery_worker.worker_app beat -S redbeat.RedBeatScheduler --pidfile= -l info
    exit $?
elif [[ "$1" = "test" ]]; then
    echo "Starting Tests"
    cd /crm/
    OPTIONS=
    if [[ "$2" = "coverage" ]]; then
        OPTIONS="--cov-report term --cov-config .coveragerc --cov=."
    elif [[ "$2" = "class" ]]; then
        OPTIONS="-k $3"
    elif [[ "$2" = "fail" ]]; then
        OPTIONS="-x"
    fi
    rm -rf /temp/prometheus_multiproc/test
    mkdir -p /temp/prometheus_multiproc/test
    export PROMETHEUS_MULTIPROC_DIR=/temp/prometheus_multiproc/test
    ENV_VAR=TEST AUTOMATED_TESTING=1 pytest -vv $OPTIONS
    exit $?
elif [[ "$1" = "create_migration" ]]; then
    python3 /crm/shared/migrations/commands/create_migration.py $2
elif [[ "$1" = "migration_down" ]]; then
    python3 /crm/shared/migrations/commands/migrate_down.py $2
else
    echo "Unknown command: $1"
fi
