from celery import Celery
from worker_app.error_handler import on_failure
from config import REDIS_HOST, REDIS_PORT, REDIS_DBS

redis_connection_string = f'redis://{REDIS_HOST}:{REDIS_PORT}'
worker_app = Celery('tasks', broker=redis_connection_string+'/'+REDIS_DBS.get('worker_app'), backend=redis_connection_string+'/'+REDIS_DBS.get('worker_app'), acks_late=True)
worker_app.conf.update(
    {
        'imports': (),
        'task_track_started': True,
        'task_acks_late': True,
        'redbeat_redis_url': redis_connection_string+'/'+REDIS_DBS.get('redbeat'),
        'beat_scheduler': 'redbeat.RedBeatScheduler',
        'redbeat_lock_key': None,
        'redbeat_lock_timeout': 90,
        'beat_max_loop_interval': 60,
        'queue_order_strategy': 'priority',
        'task_default_priority': 6,
        'broker_connection_retry': True,
        'broker_connection_retry_on_startup': True,
        'task_reject_on_worker_lost': True,
        'worker_prefetch_multiplier': 1,
        'broker_pool_limit': 100,  # Increased from 30 to handle actual usage
        'task_annotations': {'*': {'on_failure': on_failure}},
        'task_routes': {
            'worker_app.tasks.update_analytical_db.update_analytical_db': {
                'queue': 'heavy',
            },
            'worker_app.tasks.compute_csv_exports.compute_csv_data_now': {
                'queue': 'heavy',
            },
            'worker_app.tasks.compute_gogla_kpis.compute_gogla_now': {
                'queue': 'heavy',
            },
            'worker_app.tasks.send_payment_reminder_messages.send_payment_reminder_sms_now': {
                'queue': 'heavy',
            },
            'worker_app.tasks.sync_owned_devices.sync_owned_devices': {
                'queue': 'heavy',
            },
            'worker_app.tasks.update_cached_data.update_cached_data_now': {
                'queue': 'heavy',
            },
            'worker_app.tasks.check_cache_coherence.check_cached_data_now': {
                'queue': 'heavy',
            },
            'worker_app.tasks.update_usage_metrics.update_usage_metrics_for_all_applicable_devices': {
                'queue': 'heavy',
            },
            'worker_app.tasks.populate_credit_value.populate_credit_value': {
                'queue': 'heavy',
            },
            # 'worker_app.tasks.fix_first_last_answers.fix_first_answer_old': {
            #     'queue': 'heavy',
            # },
            # 'worker_app.tasks.fix_first_last_answers.fix_last_answer_old': {
            #     'queue': 'heavy',
            # },
            'worker_app.tasks.background_migrations_task.background_migration_task': {
                'queue': 'heavy',
            },
            'worker_app.tasks.update_billing_task.update_billing_task': {
                'queue': 'heavy',
            },
            'worker_app.tasks.check_db_consistency.check_db_consistency': {
                'queue': 'heavy',
            },
            'worker_app.tasks.check_adb.check_adb_coherence': {
                'queue': 'heavy',
            },
        }
    }
)
worker_app.conf.broker_transport_options = {'visibility_timeout': 3600 * 12}