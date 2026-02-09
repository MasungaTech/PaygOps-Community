from data_system.csv_exports.services.send_file_request_maker_service import SendFileRequestMaker
from worker_app.worker_app import worker_app
from shared.logger.loggers import LogAPI


@worker_app.task()
def compute_csv_data_now(tasks=None, email_user_id=None, data={}):
    try:
        if not email_user_id:
            print('Computing CSV exports...')
            SendFileRequestMaker.prepare_export_cache(tasks, data=data)
        else:
            print('Emailing CSV exports cache...')
            SendFileRequestMaker.email_export(tasks=tasks, email_user_id=email_user_id, data=data)
    except Exception as exception:
        LogAPI().FatalNoRequest(exception)
        print('Error when computing the CSV exports: '+repr(exception))
    else:
        print('Done with computing the CSV exports!')
