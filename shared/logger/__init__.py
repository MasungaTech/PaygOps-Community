import logging
from gunicorn import glogging


class IgnoreHealthChecks(logging.Filter):
    def filter(self, record):
        return record.getMessage().find('/health') == -1


class CustomLogger(glogging.Logger):

    def setup(self, cfg):
        super().setup(cfg)

        # Add filters to Gunicorn logger
        logger = logging.getLogger('werkzeug')
        logger.addFilter(IgnoreHealthChecks())
        logger = logging.getLogger("gunicorn.access")
        logger.addFilter(IgnoreHealthChecks())
        logger = logging.getLogger("gunicorn.error")
        logger.addFilter(IgnoreHealthChecks())
