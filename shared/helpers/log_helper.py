import os
from logging.handlers import RotatingFileHandler
import logging
import config


class Logger:
    FORMATTER = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    LOG_DIR = config.LOGS_DIR

    @staticmethod
    def create_handler(name, level, formatter=FORMATTER):
        handler = RotatingFileHandler(os.path.join(Logger.LOG_DIR, name),
                                      maxBytes=10000,
                                      backupCount=1)

        handler.setLevel(level)
        handler.setFormatter(formatter)

        return handler

    def create_logger(name, level=logging.DEBUG, formatter=FORMATTER):
        logger = logging.getLogger(name)
        logger.addHandler(Logger.create_handler(name, level, formatter))

        return logger

    @staticmethod
    def get_logger(name='werkzeug'):
        return logging.getLogger(name)
