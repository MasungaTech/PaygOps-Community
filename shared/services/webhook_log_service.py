from datetime import datetime
import json
from concurrent_log_handler import ConcurrentRotatingFileHandler
from config import WEBHOOK_LOG_PATH
from logging import getLogger, INFO

from shared.api_helpers.client_helpers.json_datetime_helpers import json_serializer


class WebhookLogService:
    
    # Maximum 2GB with 5 backups (10GB total)
    WRITER = getLogger('webhooks')
    WRITER.addHandler(ConcurrentRotatingFileHandler(WEBHOOK_LOG_PATH, "a", 1 * 1024 * 1024 * 1024, 5, use_gzip=True))
    WRITER.setLevel(INFO)

    @classmethod
    def insert(cls, hook, url, data):
        try:
            message = json.dumps([datetime.now(), hook, url, data], default=json_serializer)
            message = message.encode('ascii', 'ignore').decode('ascii')
            cls.WRITER.info(message)
        except Exception as e:
            print(f'Couldnt save webhook log: {str(e)}')
