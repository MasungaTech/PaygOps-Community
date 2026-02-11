from datetime import datetime
from flask_restful import Resource
from pony.orm import db_session
from shared.api_helpers.server_helpers.jwt_and_schema_verification import \
    verify
from shared.services.settings_service import SettingsService


class ForceSyncResource(Resource):

    @verify(permissions=['SuperAdmin'])
    @db_session
    def post(self):
        now = datetime.now()
        SettingsService.set_setting('LastForcedSyncTime', now)
        return {'success': True, 'message':'Sync has started in the background', 'last_full_sync_time': now.isoformat()}, 200
