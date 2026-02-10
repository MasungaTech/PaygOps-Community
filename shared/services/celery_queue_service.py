import time
from config import TEST_MODE, ENV_VAR
from worker_app.worker_app import worker_app
import redis
from shared.cache.redis_config import redis_pool
import json
from datetime import datetime
from shared.logger.loggers import LogAPI
import config

class CeleryQueueService:

    REDIS_BROKER = redis.Redis(connection_pool=redis_pool)

    LIST_QUEUES = [
        b'heavy', b'heavy\x06\x163', b'heavy\x06\x166',
        b'celery', b'celery\x06\x163', b'celery\x06\x166'
    ]
    SET_QUEUES = ['unacked']

    SINGLE_INSTANCE_TASKS = [
        'check_cached_data_now', 'update_cached_data_now', 'update_analytical_db',
        'compute_csv_data_now', 'backup_file_now', 'fix_payment_processing',
        'check-adb-coherence', 'send_payment_reminder_sms_now', 'check_db_consistency',
        'update_contract_status'
    ]

    @classmethod
    def get_all_tasks(cls):
        if ENV_VAR == 'TEST': return []
        live = cls.get_live_tasks()
        tasks_clean = live
        existing_id = [task['id'] for task in tasks_clean]
        for task in cls.get_queued_tasks():
            if task['id'] not in existing_id:
                tasks_clean.append(task)
                existing_id.append(task['id'])
        return tasks_clean

    @classmethod
    def get_live_tasks(cls):
        # Inspect all nodes.
        i = worker_app.control.inspect()
        # Get tasks that have an ETA or are scheduled for later processing
        scheduled = cls._get_tasks_list_from_dict(i.scheduled(), 'scheduled')
        # Get tasks that have been claimed by workers
        claimed = cls._get_tasks_list_from_dict(i.reserved(), 'claimed')
        # Get tasks that are currently running.
        active = cls._get_tasks_list_from_dict(i.active(), 'running')
        return scheduled+active+claimed

    @classmethod
    def get_queued_tasks(cls):
        heavy = []
        unacked = []
        for queue_name in cls.LIST_QUEUES:
            heavy += cls.get_celery_list_queue_items(queue_name)
        for queue_name in cls.SET_QUEUES:
            unacked += cls.get_celery_set_queue_items(queue_name)
        return heavy + unacked

    @classmethod
    def kill_live_task(cls, task_id):
        worker_app.control.revoke(task_id, terminate=True)

    @classmethod
    def kill_queued_tasks(cls, task_ids):
        for queue_name in cls.LIST_QUEUES:
            cls._kill_queued_tasks_in_list_queue(task_ids, queue_name)
        for queue_name in cls.SET_QUEUES:
            cls._kill_queued_tasks_in_set_queue(task_ids, queue_name)

    @classmethod
    def groom_queue(cls):
        queued_tasks = cls.get_queued_tasks()
        already_queued = []
        to_kill = []
        for task in queued_tasks:
            name = task['name'].split('.')[-1]
            if name in cls.SINGLE_INSTANCE_TASKS:
                if name in already_queued:
                    to_kill.append(task['id'])
                else:
                    already_queued.append(name)
        cls.kill_queued_tasks(to_kill)

    @classmethod
    def check_long_running_tasks(cls):
        now = datetime.now().timestamp()
        live_tasks = cls.get_live_tasks()
        for task in live_tasks:
            if task['time_start']:
                runtime_minutes = (now - task['time_start'])/60
                name = task["name"].split(".")[-1]
                if runtime_minutes > config.RUNTIME_WARNING_THRESHOLD:
                    LogAPI.Warning(f'Task [{name}] has been running for [{round(runtime_minutes)}] min')

    @classmethod
    def kill_long_running_tasks(cls):
        now = datetime.now().timestamp()
        live_tasks = cls.get_live_tasks()
        for task in live_tasks:
            if task['time_start']:
                runtime_minutes = (now - task['time_start'])/60
                name = task["name"].split(".")[-1]
                if runtime_minutes > config.LONG_RUNNING_TASK_THRESHOLD:
                    LogAPI.Warning(f'Killing task [{name}] because it has been running for [{round(runtime_minutes)}] min')
                    cls.kill_live_task(task['id'])

    @classmethod
    def check_queue_length(cls):
        queued_tasks = cls.get_queued_tasks()
        nb_tasks = len(queued_tasks)
        if nb_tasks > config.QUEUED_TASK_WARNING_THRESHOLD:
            LogAPI.Warning(f'There are [{nb_tasks}] running')

    @classmethod
    def _kill_queued_tasks_in_list_queue(cls, task_ids, queue_name):
        tasks = cls._get_celery_list_queue(queue_name)
        for task in tasks:
            t = json.loads(task)
            if isinstance(t, dict):
                id = t.get('headers', {}).get('id')
                if str(id) in task_ids:
                    cls.REDIS_BROKER.lrem(queue_name, -1, task)

    @classmethod
    def _kill_queued_tasks_in_set_queue(cls, task_ids, queue_name):
        tasks = cls._get_celery_set_queue(queue_name)
        for task in tasks:
            j = json.loads(tasks[task])[0]
            if isinstance(j, dict):
                id = j.get('headers', {}).get('id')
                if str(id) in task_ids:
                    cls.REDIS_BROKER.hdel(queue_name, task)

    @classmethod
    def purge_live_tasks(cls):
        worker_app.control.purge()

    @classmethod
    def purge_queued_tasks(cls):
        conn = cls.REDIS_BROKER
        for queue_name in cls.LIST_QUEUES+cls.SET_QUEUES:
            conn.delete(queue_name)
    
    @classmethod
    def purge_unacked_tasks(cls, threshold=None):
        if not threshold: threshold = time.time()
        conn = cls.REDIS_BROKER
        for queue_name in cls.SET_QUEUES:
            tasks = conn.zrangebyscore(f'{queue_name}_index', "-inf", threshold)
            for task in tasks:
                task = conn.hdel(queue_name, task)

    @classmethod
    def _get_tasks_list_from_dict(cls, task_dict, status):
        if not task_dict:
            return []
        all_tasks = []
        for worker_tasks in task_dict:
            tasks = task_dict[worker_tasks]
            for task in tasks:
                task['status'] = status
                all_tasks.append(task)
        return all_tasks

    @classmethod
    def get_celery_set_queue_items(cls, queue_name):
        tasks = cls._get_celery_set_queue(queue_name)
        decoded_tasks = []
        for task in tasks:
            t = json.loads(tasks[task])[0]
            if isinstance(t, dict):
                t = cls._extract_task_data(t)
                t['unacked'] = True
                t['score'] = cls.REDIS_BROKER.zscore(f'{queue_name}_index', task)
                decoded_tasks.append(t)
        return decoded_tasks

    @classmethod
    def get_celery_list_queue_items(cls, queue_name):
        decoded_tasks = []
        for task in cls._get_celery_list_queue(queue_name):
            t = json.loads(task)
            if isinstance(t, dict):
                decoded_tasks.append(cls._extract_task_data(t))
        return decoded_tasks

    @classmethod
    def _get_celery_list_queue(cls, queue_name):
        conn = cls.REDIS_BROKER
        tasks = conn.lrange(queue_name, 0, -1)
        if not tasks:
            return []
        return tasks

    @classmethod
    def _get_celery_set_queue(cls, queue_name):
        conn = cls.REDIS_BROKER
        tasks = conn.hgetall(queue_name)
        if not tasks:
            return []
        return tasks

    @classmethod
    def _extract_task_data(cls, j):
        tinfo = j['headers']
        tinfo['status'] = 'queued'
        tinfo['name'] = tinfo['task']
        tinfo.update(j['properties'])
        tinfo['delivery_info']['priority'] = tinfo['priority']
        return tinfo

    @classmethod
    def is_task_running(cls, task_name):
        if ENV_VAR == 'TEST': return False
        for t in cls.get_live_tasks():
            if task_name in t.get('name'):
                return True
        return False

    @classmethod
    def is_task_running_or_queued(cls, task_name):
        return task_name in [t.get('name') for t in cls.get_all_tasks()]

    @classmethod
    def is_task_id_running(cls, task_id):
        for t in cls.get_live_tasks():
            if task_id in t.get('id'):
                return True
        return False
    
    @classmethod
    def get_registered_tasks(cls):
        if ENV_VAR == 'TEST': return []
        INVALID_TASKS = ['map', 'chord_unlock', 'starmap', 'chunks', 'group', 'chain', 'accumulate', 'chord']
        task_list = list(worker_app.tasks.keys())
        clean_task_list = []
        for task in task_list:
            if task.split('.')[-1] not in INVALID_TASKS:
                clean_task_list.append(task)
        return clean_task_list
                
    @classmethod
    def execute_task_by_name(cls, task_name, *args, **params):
        if ENV_VAR == 'TEST': return
        short_name = task_name.split('.')[-1]
        if short_name in cls.SINGLE_INSTANCE_TASKS:
            print(f'Checking if task {short_name} running')
            if cls.is_task_running_or_queued(task_name):
                print('Task Already Launched')
                return
        print(f'Launching task {short_name}')
        worker_app.send_task(task_name, args=args, kwargs=params)
    
    @classmethod
    def execute_task(cls, task, *args, **kwargs):
        if TEST_MODE: task(*args, **kwargs)
        else: cls.execute_task_by_name(task.name, *args, **kwargs)
    