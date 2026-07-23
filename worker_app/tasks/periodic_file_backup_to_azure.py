from datetime import datetime, timedelta
from pony.orm import db_session
from shared.file_upload.model import StoredFile
from shared.file_upload.services.stored_file_service import StoredFileService
from shared.logger.loggers import LogAPI
from worker_app.tasks.background_migrations_task import BackgroundMigrations
from worker_app.worker_app import worker_app
from config import (
   BACKUP_FILE_TIME_DELAY, WABS_ACCOUNT_NAME, WABS_ACCESS_KEY, IS_TEST_PLATFORM
)
from azure.storage.blob import BlobServiceClient

CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net'


@worker_app.task
@db_session
def backup_files_not_previously_uploaded(overwrite=True):
   if IS_TEST_PLATFORM:
      return # We do not run this on test platforms
    
   threshold_date = datetime.now()-timedelta(seconds=BACKUP_FILE_TIME_DELAY)
   backupable_records = StoredFileService.get_list(threshold=threshold_date).filter(lambda f: f.available).order_by(lambda l: l.id)
   print('backupable_records count: '+str(backupable_records.count()))

   blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING.format(
      account_name=WABS_ACCOUNT_NAME,
      account_key=WABS_ACCESS_KEY,
   ))
   def task(file):
      if not file.is_found():
         LogAPI.Warning(f'File [{file.uuid}] is marked as available but not found in the server')
         file.available = False
         return
      StoredFileService.backup_file_from_client_and_object(blob_service_client, file, overwrite=overwrite)
   BackgroundMigrations.chunk_executer(backupable_records, StoredFile, task, 'file backups on azure')
