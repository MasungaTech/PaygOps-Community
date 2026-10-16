from pony import orm
from config import API_PREFIX
from shared.model.activity_log_model import ActivityLogEntry
from core_system.users.models.user_model import User
import time
from mock import patch
import config


class TestActivityLogService:
    
    @orm.db_session
    def test_end_to_end_api_log_post(self, api_client, good_api_key):
        resp = api_client.post(API_PREFIX + '/test_route', json={"test_name": "name", "test_number": 3}, headers={'Authorization': 'Bearer ' + good_api_key})
        print(resp.json)
        log = self._get_last_log()
        assert log.user == 1
        assert log.ip == '127.0.0.1'
        assert log.path == API_PREFIX + '/test_route'
        assert not log.args
        assert log.data == {"test_name": "name", "test_number": 3}
        assert log.app == "api_app"
        
    @orm.db_session
    def test_end_to_end_api_log_get(self, api_client, good_api_key):
        api_client.get(API_PREFIX + '/test_route?test=api_get', headers={'Authorization': 'Bearer ' + good_api_key})
        log = self._get_last_log()
        assert log.user == 1
        assert log.ip == '127.0.0.1'
        assert log.path == API_PREFIX + '/test_route'
        assert log.args == {"test": "api_get"}
        assert not log.data
        assert log.app == "api_app"

    def test_end_to_end_web_log_post(self, super_admin_app):
        with orm.db_session:
            super_admin_app.post('/interactions/', data={"test": "api post"})
        with orm.db_session:
            log = self._get_last_log()
            assert log.user == User.get(username="super_admin@test.com").id
            assert log.ip == '127.0.0.1'
            assert log.path == '/interactions/'
            assert not log.args
            assert log.data == {"test": "api post"}
            assert log.app == "web_app"

    def test_end_to_end_web_log_get(self, super_admin_app):
        with orm.db_session:
            super_admin_app.get('/?test=api_get', follow_redirects=False)
        with orm.db_session:
            log = self._get_last_log()
            assert log.user == User.get(username="super_admin@test.com").id
            assert log.ip == '127.0.0.1'
            assert log.path == '/'
            assert log.args == {"test": "api_get"}
            assert not log.data
            assert log.app == "web_app"
    
    @classmethod
    def _get_last_log(cls):
        return ActivityLogEntry.select().order_by(orm.desc(ActivityLogEntry.time)).first()
