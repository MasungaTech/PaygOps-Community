from worker_app.worker_app import worker_app
from shared.logger.loggers import LogAPI
import config
log_api = LogAPI()


@worker_app.task
def update_analytical_db(*args, update_stats=True, force_models=['Contracts'], daily_update=False, **kwargs):
    if config.DISABLE_ANALYTICAL_DB:
        return 
    from data_system.analytical_db.services.update_service import AnalyticalDBUpdateService
    from data_system.analytical_db.services.stats_update_service import AnalyticalDBStatsUpdateService
    from payg_loan_system.devices.services.device_metrics_service import DeviceMetricsService
    try:
        DeviceMetricsService.update_all_device_metrics()  # Only needed the first time
    except Exception as e:
        log_api.Fatal(e)
    try:
        AnalyticalDBUpdateService.update(force_models=force_models, daily_update=daily_update)
        if update_stats:
            AnalyticalDBStatsUpdateService.update()
    except Exception as e:
        log_api.Fatal(e)
        log_api.Event('Error in update attempt. Details: '+str(e))
