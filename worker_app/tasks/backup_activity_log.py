from datetime import datetime, timedelta
import os
from shared.services.activity_log_service import ActivityLogGetter
from pony.orm import db_session, commit
from worker_app.worker_app import worker_app
from data_system.csv_exports.services.simple_activity_log_export_service import SimpleActivityLogExportService
from shared.logger.loggers import LogAPI
from azure.storage.blob import BlobServiceClient
from config import (
    ACTIVITY_LOG_BACKUP_PERIOD, ACTIVITY_LOG_PATH, ACTIVITY_LOG_BACKUP_MINSIZE,
    ACTIVITY_LOG_BACKUP_MAXSIZE, WABS_ACCESS_KEY, WABS_ACCOUNT_NAME, WALE_CONTAINER_NAME
)

CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net'


@worker_app.task
@db_session
def backup_activity_log_now(force_now=False):
    
    if force_now:
        threshold_date = datetime.now()
    else:
        threshold_date = datetime.now()-timedelta(days=30*ACTIVITY_LOG_BACKUP_PERIOD)
    backupable_records = ActivityLogGetter.get_list(threshold=threshold_date).order_by(lambda l: l.id)

    blob_service_client = None
    try:
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING.format(
            account_name=WABS_ACCOUNT_NAME,
            account_key=WABS_ACCESS_KEY,
        ))
    except Exception as error:
        LogAPI.FatalNoRequest(error) # Notify team to avoid accumulation of files
        print('Error getting WABS client')
    
    def upload_local_backup_file(filename):
        if not blob_service_client:
            return
        try:
            print("Uploading to Azure Storage as blob: " + filename)
            # Create a blob client using the local file name as the name for the blob
            blob_client = blob_service_client.get_blob_client(container=WALE_CONTAINER_NAME, blob='activity_log/'+filename)
            # Upload the created file
            with open(ACTIVITY_LOG_PATH + filename, "rb") as data:
                blob_client.upload_blob(data)
            # remove local file
            os.remove(ACTIVITY_LOG_PATH + filename)
        except Exception as error:
            LogAPI.FatalNoRequest(error) # Notify team to avoid accumulation of files
            print('Error uploading file')

    if not os.path.exists(ACTIVITY_LOG_PATH):
        os.mkdir(ACTIVITY_LOG_PATH)

    counter = 0
    cf = 1
    while backupable_records.count() >= ACTIVITY_LOG_BACKUP_MINSIZE and counter < 5: # limit number of files per execution
        counter += 1
        try:

            last_record_position = backupable_records.count() if backupable_records.count() < ACTIVITY_LOG_BACKUP_MAXSIZE else ACTIVITY_LOG_BACKUP_MAXSIZE
            last_id_to_backup = backupable_records.limit(1, offset=last_record_position-1)[:][0].id

            filename = f'activity_log_backup-{threshold_date:%Y-%m-%dT%H-%M-%SZ}_{cf}.zip'
            zip_file_path = ACTIVITY_LOG_PATH + filename
            
            if os.path.isfile(zip_file_path):
                raise Exception('The filename is already existing')
            SimpleActivityLogExportService.get_simple_export(last_id_to_backup, zip_file_path)

            print('Activity Log Backup Saved')

        except Exception as exception:
            LogAPI.FatalNoRequest(exception)
            print('Error in Activity Log backup: '+repr(exception))
            if os.path.isfile(zip_file_path):
                os.remove(zip_file_path)
        else:
            cf += 1
            ActivityLogGetter.get_list(last_id=last_id_to_backup).delete(bulk=True)
            commit()
            upload_local_backup_file(filename)
    
    print('Uploading local files not yet uploaded')
    for filename in os.listdir(ACTIVITY_LOG_PATH):
        # check if current path is a file
        if os.path.isfile(os.path.join(ACTIVITY_LOG_PATH, filename)):
            upload_local_backup_file(filename)
