from datetime import datetime
import json
from concurrent_log_handler import ConcurrentRotatingFileHandler
from config import ACCESS_LOG_PATH
from werkzeug.exceptions import BadRequest
from shared.services.activity_log_service import ActivityLogService
from core_system.users.models.user_model import User
import copy
from logging import getLogger, INFO
from shared.helpers.user_agent_parser import RequestUserAgentParser


class AccessLogService:
    
    LEGACY_LOG_ENABLED = True
    # Maximum 2GB with 5 backups (10GB total)
    WRITER = getLogger('access_log')
    WRITER.addHandler(ConcurrentRotatingFileHandler(ACCESS_LOG_PATH, "a", 2 * 1024 * 1024 * 1024, 5, use_gzip=True))
    WRITER.setLevel(INFO)

    @classmethod
    def insert(cls, request, app, user_id):
        data = cls.get_clean_data_from_request(request, app)
        access_log = {
            'time': str(datetime.now()),
            'app': app,
            'ip': str(request.environ.get('HTTP_X_REAL_IP', request.remote_addr)),
            'agent': RequestUserAgentParser.get_short_agent_string(request),
            'user_id': user_id or None,
            'url': str(request.path),
            'data': data,
            'args': request.args,
            'method': request.method,
        }
        try:
            message = json.dumps(access_log)
            message = message.encode('ascii', 'ignore').decode('ascii')
            cls.WRITER.info(message)
        except Exception as e:
            print(f'Couldnt save access log: {str(e)}')
        
        if cls.LEGACY_LOG_ENABLED:
            try:
                fresh_user = User.get(id=user_id) if user_id else None
                ActivityLogService.insert(request, data, app, fresh_user)
            except Exception as e:
                print(f'Couldnt save activity log: {str(e)}')

    @classmethod
    def get_clean_data_from_request(cls, request, app):
        data = request.form
        json_data = None
        if request.content_type == 'application/json':
            try:
                json_data = request.json
            except BadRequest:
                json_data = None
        clean_data = json_data or data
        if app == 'mobile_sync_app':
            # We do some cleaning of the sync data before storing
            # We remove the key entirely if there's no change
            # Otherwise we remove jus the map of IDs
            clean_data = copy.deepcopy(clean_data) if clean_data else {}
            for key in list(clean_data.keys()):
                if isinstance(clean_data[key], dict):
                    if 'allCrmIdsOnMobileMap' in clean_data[key]:
                        if not clean_data[key].get('toInsertOnServer') and not clean_data[key].get('toUpdateOnServer'):
                            del clean_data[key]
                        else:
                            del clean_data[key]['allCrmIdsOnMobileMap']
        return clean_data