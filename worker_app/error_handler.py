from shared.logger.loggers import LogAPI

def on_failure(self, exc, task_id, args, kwargs, einfo):
    LogAPI.Fatal(exc)
