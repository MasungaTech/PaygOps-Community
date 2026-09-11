from shared.logger.loggers import Error, LogAPI
from shared.services.background_task_base import BackgroundTask
from shared.services.bulk_upload_task_processors import BulkUploadTaskProcessors
from worker_app.worker_app import worker_app
from pony.orm import db_session
from celery import group


@worker_app.task
def process_bulk_entity_upload(uuid):

    print('Processing bulk entity upload...')
    task_service = BackgroundTask(uuid)
    task_service.status = 'processing'

    total_rows = len(task_service.data)
    task_service.update_processing_progress(0, total_rows, 'Starting processing...')

    # When unordered is true, process in parallel via independent tasks
    if getattr(task_service, 'unordered', 'false') == 'true':
        task_service.update_processing_progress(0, total_rows, 'Processing rows in parallel...')
        
        # Define a lightweight wrapper task dynamically for parallel execution
        @worker_app.task(name=f"worker_app.tasks.process_single_line.{uuid}")
        def process_single_line(data_line):
            try:
                getattr(BulkUploadTaskProcessors, task_service.entity)(data_line, task_service)
            except Error as error:
                with db_session:
                    task_service.append_processing_error(error.get_message(), line=data_line[2])
            except Exception as exception:
                task_service.append_processing_error(str(exception), line=data_line[2])
                LogAPI.FatalNoRequest(exception)
            return True

        job = group(process_single_line.s(data_line) for data_line in task_service.data)
        result = job.apply_async()
        result.join()
        
        # Update progress to complete
        task_service.update_processing_progress(total_rows, total_rows, 'Parallel processing complete')
    else:
        # Sequential processing with progress updates
        for i, data_line in enumerate(task_service.data):
            try:
                getattr(BulkUploadTaskProcessors, task_service.entity)(data_line, task_service)
            except Error as error:
                with db_session:
                    task_service.append_processing_error(error.get_message(), line=data_line[2])
            except Exception as exception:
                task_service.append_processing_error(str(exception), line=data_line[2])
                LogAPI.FatalNoRequest(exception)
            
            # Update progress every 10 rows or on last row
            if (i + 1) % 10 == 0 or (i + 1) == total_rows:
                task_service.update_processing_progress(i + 1, total_rows)

    task_service.complete_processing()
