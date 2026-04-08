from worker_app.worker_app import worker_app
from shared.logger.loggers import LogService
from data_system.analytical_db.services.adb_check_service import ADBCheckService
import config


@worker_app.task
def check_adb_running():
    if config.DISABLE_ANALYTICAL_DB:
        return 
    LogService.Event('Checking if Analytical DB is running...')
    ADBCheckService.warn_if_last_update_too_old()


@worker_app.task
def check_adb_coherence():
    if config.DISABLE_ANALYTICAL_DB:
        return 
    LogService.Event('Checking if Analytical DB is coherent...')
    ADBCheckService.warn_if_updated_objects_have_mismatching_data()
