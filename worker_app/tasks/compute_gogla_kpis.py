from worker_app.worker_app import worker_app
from shared.logger.loggers import LogAPI
from payg_loan_system.gogla_stats.gather import run_gogla_stats


@worker_app.task
def compute_gogla_now():
    print('Computing GOGLA stats...')
    try:
        run_gogla_stats()
    except Exception as exception:
        LogAPI().FatalNoRequest(exception)
        print('Error when computing the GOGLA KPIs: '+repr(exception))
    else:
        print('Done with computing GOGLA KPIs!')
