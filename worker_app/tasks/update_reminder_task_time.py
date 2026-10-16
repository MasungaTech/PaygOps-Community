from shared.services.celery_queue_service import CeleryQueueService
from worker_app.worker_app import worker_app


@worker_app.task
def update_payment_reminder_time():
    # We need to import that here to avoid circular import issues
    from worker_app.periodic_tasks_service import PeriodicTasksService
    print('Updating payment reminder time...')
    PeriodicTasksService.update_payment_reminder_task()


def run_update_payment_reminder_time():
    print('Updating payment reminder time...')
    # This needs to run in a celery task to be able to change the task time
    CeleryQueueService.execute_task(update_payment_reminder_time)
