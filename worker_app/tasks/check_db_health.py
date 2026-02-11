from pony.orm import db_session
from worker_app.worker_app import worker_app
from shared.logger.loggers import LogService
from core_system.core_entities import db as mdb
from datetime import datetime, timedelta
from shared.cache.redis_config import set_cache_key, get_cache_key


@worker_app.task
@db_session
def check_db_health(*args, **kwargs):
    EXPECTED_LONG_QUERIES = ['pg_start_backup', 'pg_stop_backup', 'pg_sleep']
    QUERY_WARNING_THRESHOLD = 60 # In seconds
    LONG_QUERY_WARNING_THRESHOLD = 60*15 # 15 minutes
    SECONDS_BETWEEN_ALERTS = 60*120 # 2 hours
    QUERY = f'''
        SELECT
        pid,
        now() - pg_stat_activity.xact_start AS duration,
        query,
        state
        FROM pg_stat_activity
        WHERE (now() - pg_stat_activity.query_start) > interval '{QUERY_WARNING_THRESHOLD} seconds'
        AND state = 'active';
    '''
    long_running_queries_raw = mdb.execute(QUERY).fetchall()
    long_running_queries = []
    # We remove the expected long queries from there
    for query in long_running_queries_raw:
        to_alert = True
        # We check if it's not one expected to be long
        for long_name in EXPECTED_LONG_QUERIES:
            if long_name in str(query[2]):
                # If expected to be long, then we check if over the other threshold
                if query[1] < timedelta(seconds=LONG_QUERY_WARNING_THRESHOLD):
                    to_alert = False
        # We check if it was not already reported recently
        cache_key = 'long_running_query_'+str(query[0])
        if get_cache_key(cache_key) is None:
            if to_alert:
                set_cache_key(cache_key, 'true', seconds_to_expiry=SECONDS_BETWEEN_ALERTS)
        else:
            to_alert = False
        # If not long or long enough and not already reported recently, we alert 
        if to_alert:
            long_running_queries.append(query)
    if len(long_running_queries) > 0:
        LogService.Warning(f'Found [{len(long_running_queries)}] long running queries', other_data={'queries': str(long_running_queries) })


@worker_app.task
@db_session
def kill_long_running_queries(*args, **kwargs):
    QUERY_KILL_THRESHOLD = 60 # In seconds
    QUERY = f'''
        SELECT pg_cancel_backend(pid) 
        FROM pg_stat_activity 
        WHERE state = 'active' 
        AND (now() - pg_stat_activity.query_start) > interval '{QUERY_KILL_THRESHOLD} seconds'
        AND pid <> pg_backend_pid();
    '''
    killed_queries = mdb.execute(QUERY).fetchall()
    if len(killed_queries) > 0:
        LogService.Warning(f'Killed [{len(killed_queries)}] long running queries: [{str(killed_queries)}]')
