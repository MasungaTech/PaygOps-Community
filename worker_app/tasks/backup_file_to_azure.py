from pony.orm import db_session
from shared.file_upload.services.stored_file_service import StoredFileService
from worker_app.worker_app import worker_app


@worker_app.task
@db_session
def backup_file_now(uuid):
    file_object = StoredFileService.get_from_uuid(uuid)
    if not file_object: raise Exception(f'File to backup with uuid [{uuid}] not found')
    StoredFileService.backup_file(file_object)
