from datetime import time
import datetime
from celery.schedules import crontab
from redbeat import RedBeatSchedulerEntry
from worker_app.tasks.periodic_file_backup_to_azure import backup_files_not_previously_uploaded
from worker_app.tasks.update_contract_status import update_contract_status
from worker_app.worker_app import worker_app
from worker_app.tasks.compute_gogla_kpis import compute_gogla_now
from worker_app.tasks.send_payment_reminder_messages import send_payment_reminder_sms_now
from worker_app.tasks.compute_csv_exports import compute_csv_data_now
from worker_app.tasks.update_usage_metrics import update_usage_metrics_for_all_applicable_devices
from worker_app.tasks.update_cached_data import update_cached_data_now
from worker_app.tasks.check_cache_coherence import check_cached_data_now
from worker_app.tasks.backup_activity_log import backup_activity_log_now
from worker_app.tasks.update_analytical_db import update_analytical_db
from worker_app.tasks.celery_queue_groomer import celery_queue_groomer, celery_queue_alerter
from worker_app.tasks.fix_payment_processing import fix_payment_processing
from worker_app.tasks.try_reconcile_pending_payments import try_reconcile_pending_payments
from worker_app.tasks.check_db_consistency import check_db_consistency
from worker_app.tasks.autoreconciliation import autoreconciliate, autoreconciliate_week
from worker_app.tasks.update_billing_task import update_billing_task
from worker_app.tasks.update_billing_config import update_billing_config_task
from worker_app.tasks.healthcheck import beat_healthcheck
from worker_green_app.tasks.green_healthcheck import green_healthcheck
from worker_app.tasks.check_adb import check_adb_running, check_adb_coherence
from worker_app.tasks.check_redis_status_reports import check_redis_status_reports
from worker_app.tasks.check_db_health import check_db_health
from shared.services.settings_service import SettingsService
from shared.helpers.clock import Clock
from config import ACTIVITY_LOG_BACKUP_PERIOD, is_production_server, FREQUENT_ADB_UPDATE, ENABLE_ENTERPRISE_FEATURES
from pony import orm


class PeriodicTasksService:

    @classmethod
    @orm.db_session
    def set_periodic_tasks(cls, sender):
        PERIODIC_TASKS = [
            {'name': 'compute-gogla-every-monday-morning', 'function': compute_gogla_now.s(), 'schedule': cls._local_cron(time(0, 0), day_of_month='1')},
            {'name': 'activity-log-backup', 'function': backup_activity_log_now.s(), 'schedule': cls._local_cron(time(0, 15), day_of_month='*')},
            {'name': 'update-analytical-db-0', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(0, 30)), 'task_kwargs': {'daily_update': True}},
            {'name': 'update-analytical-db-3', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(3, 30))},
            {'name': 'update-analytical-db-6', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(6, 30))},
            {'name': 'update-analytical-db-9', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(9, 30))},
            {'name': 'update-analytical-db-12', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(12, 30))},
            {'name': 'update-analytical-db-15', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(15, 30))},
            {'name': 'update-analytical-db-18', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(18, 30))},
            {'name': 'update-analytical-db-21', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(21, 30))},
            {'name': 'check-adb-running', 'function': check_adb_running.s(), 'schedule': crontab(minute=5, hour='*/1')},
            {'name': 'check-adb-coherence', 'function': check_adb_coherence.s(), 'schedule': cls._local_cron(time(23, 30))},
            {'name': 'generate-csv-day', 'function': compute_csv_data_now.s(), 'schedule': cls._local_cron(time(0, 31))},
            {'name': 'check_cached_data', 'function': check_cached_data_now.s(), 'schedule': cls._local_cron(time(0, 32))},
            {'name': 'send-payment-reminder-every-day', 'function': send_payment_reminder_sms_now.s(), 'schedule': cls._local_cron(SettingsService.get_setting('TimeSendingPaymentReminder'))},
            {'name': 'beat-healthcheck', 'function': beat_healthcheck.s(), 'schedule': crontab(minute='*/1'), 'production_only': True},
            {'name': 'check_db_health', 'function': check_db_health.s(), 'schedule': crontab(minute='*/2'), 'production_only': True},
            {'name': 'fix_payment_processing', 'function': fix_payment_processing.s(), 'schedule': crontab(minute=30, hour='*/1')},
            {'name': 'check_db_consistency', 'function': check_db_consistency.s(), 'schedule': cls._local_cron(time(3, 15), day_of_week='1-6')},
            {'name': 'check_db_consistency_with_costly_checks', 'function': check_db_consistency.s(), 'schedule': cls._local_cron(time(3, 15), day_of_week='0'), 'task_kwargs': {'costly_checks': True}},
            {'name': 'autoreconcile', 'function': autoreconciliate.s(), 'schedule': crontab(minute='*/5')},
            {'name': 'autoreconcile-week', 'function': autoreconciliate_week.s(), 'schedule': crontab(minute='*/30')},
            {'name': 'celery-groom', 'function': celery_queue_groomer.s(), 'schedule': crontab(minute='*/5')},
            {'name': 'check-redis-status-reports', 'function': check_redis_status_reports.s(), 'schedule': crontab(minute='*/2')},
            {'name': 'celery-alerter', 'function': celery_queue_alerter.s(), 'schedule': crontab(minute='*/30')},
            {'name': 'update_cached_data', 'function': update_cached_data_now.s(), 'schedule': crontab(minute=0, hour='*')},
            {'name': 'update_usage_metrics_for_all_applicable_devices', 'function': update_usage_metrics_for_all_applicable_devices.s(), 'schedule': crontab(minute=0, hour='*')},
            {'name': 'update-contract-status-daily', 'function': update_contract_status.s(), 'schedule': crontab(minute=0, hour=0)},
            {'name': 'backup_files_not_previously_uploaded', 'function': backup_files_not_previously_uploaded.s() , 'schedule': crontab(minute=0, hour='*/1')},
            {'name': 'try-reconcile-pending-payments', 'function': try_reconcile_pending_payments.s(), 'schedule': cls._local_cron(time(2, 0), day_of_month='*')},
        ]

        if ENABLE_ENTERPRISE_FEATURES:
            PERIODIC_TASKS += [
                {'name': 'update-billing-config', 'function': update_billing_config_task.s(), 'schedule': crontab(minute=2, hour=3, day_of_month='*')},
                {'name': 'update-billing-consolidated', 'function': update_billing_task.s(), 'schedule': cls._local_cron(time(3, 31), day_of_month='1')}, # this is the last processing of the previous month billing
                {'name': 'update-billing-first-partial', 'function': update_billing_task.s(), 'schedule': cls._local_cron(time(3, 31), day_of_month='2')}, # this is the first processing of the current month, we need to do it to ensure the is a bill created for the current month
                {'name': 'update-billing-partial', 'function': update_billing_task.s(), 'schedule': cls._local_cron(time(3, 31), day_of_month='3-31', day_of_week='0')}, # we update the current month bill every week on sundays
            ]

        if FREQUENT_ADB_UPDATE:
            PERIODIC_TASKS += [
                {'name': 'update-analytical-db-5', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(5, 00))},
                {'name': 'update-analytical-db-8', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(8, 00))},
                {'name': 'update-analytical-db-11', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(11, 00))},
                {'name': 'update-analytical-db-14', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(14, 00))},
                {'name': 'update-analytical-db-17', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(17, 00))},
                {'name': 'update-analytical-db-20', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(20, 00))},
                {'name': 'update-analytical-db-23', 'function': update_analytical_db.s(), 'schedule': cls._local_cron(time(23, 00))}
            ]
        
        for task in PERIODIC_TASKS:
            if not cls._is_task_registered(task['name']) and (not task.get('production_only') or is_production_server()):
                print(f'Registering task {task["name"]}...')
                sender.add_periodic_task(
                    task['schedule'],
                    task['function'],
                    name=task['name'],
                    kwargs=task.get('task_kwargs', {})
                )
            else:
                print(f'Task {task["name"]} already registered')
        
        from app_builder_system.automations.services.automation_service import AutomationService
        AutomationService.register_all_automation_periodic_tasks()

    @classmethod
    def _is_task_registered(cls, task_name):
        if task_name in worker_app.conf.beat_schedule:
            return True
        else:
            return False
        
    @staticmethod
    def _local_cron(local_time=None, **kwargs):
        if local_time and isinstance(local_time, datetime.time):
            print(f"[local_cron] Converting local_time: {local_time}")
            server_time = Clock.localize_to_utc(local_time)
            # Use time from localized conversion unless overridden by kwargs
            minute = kwargs.pop("minute", server_time.minute)
            hour = kwargs.pop("hour", server_time.hour)
        else:
            # Default to wildcards if no specific local_time provided
            minute = kwargs.pop("minute", "*")
            hour = kwargs.pop("hour", "*")
        return crontab(minute=minute, hour=hour, **kwargs)

    @classmethod
    @orm.db_session
    def update_payment_reminder_task(cls):
        time_of_day = SettingsService.get_setting('TimeSendingPaymentReminder')
        new_schedule = cls._local_cron(time_of_day)
        entry = RedBeatSchedulerEntry(
            'send-payment-reminder-every-day',
            'worker_app.tasks.send_payment_reminder_messages.send_payment_reminder_sms_now',
            new_schedule,
            app=worker_app,
        )
        entry.save()


    @classmethod
    def add_periodic_task(cls, name, function, schedule, task_kwargs=None):
        print(f"[add_periodic_task] name: {name}")
        print(f"[add_periodic_task] function: {function}")
        print(f"[add_periodic_task] schedule: {schedule}")
        print(f"[add_periodic_task] task_kwargs: {task_kwargs}")    
        worker_app.add_periodic_task(
            schedule,
            function,
            name=name,
            kwargs=task_kwargs or {}
        )

    @classmethod
    def add_redbeat_periodic_task(cls, name, function_path, schedule, task_kwargs=None):
        entry = RedBeatSchedulerEntry(
            name=name,
            task=function_path,
            schedule=schedule,
            app=worker_app,
            kwargs=task_kwargs or {}
        )
        entry.save()


    # from redbeat.schedulers import RedBeatSchedulerEntry

    @classmethod
    def remove_automation_task_if_registered(cls, automation):
        task_name = f'run-automation-{automation.uuid}'

        # Remove from in-memory config
        if task_name in worker_app.conf.beat_schedule:
            del worker_app.conf.beat_schedule[task_name]
            print(f"[PeriodicTasksService] Removed in-memory beat_schedule task: {task_name}")

