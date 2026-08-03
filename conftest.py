from pony.orm import db_session
from datetime import datetime, timedelta
from contextlib import contextmanager
from mock import patch
import pytest
from celery.app.task import Task
from flask import template_rendered
from web_app import app as web_app
from config import ENABLE_ENTERPRISE_FEATURES
if ENABLE_ENTERPRISE_FEATURES:
    from mobile_sync_app import app as mobile_api
from tests.factories.database_seeder import DatabaseSeeder
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt
import config
from api_app import api_app
from core_system.role.permissions import all_permissions
from core_system.role.migrations.update_permissions import generate_permission_list_from_dict
from core_system.core_entities import db

Task.apply_async = Task.apply
DatabaseSeeder.create_db()
DatabaseSeeder.init_default_data()


@contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def configure(app, server_name="localhost"):
    app.config['SERVER_NAME'] = server_name
    app.config['DATABASE'] = "sqlite://"
    app.config['SESSION_COOKIE_DOMAIN'] = False
    app.testing = True
    return app


@pytest.fixture(scope="module")
def app():
    return configure(web_app)


@pytest.fixture(scope="module")
def sms_application():
    return configure(api_app, "localhost:6789")


@pytest.fixture(scope="module")
def mobile_api_app():
    return configure(mobile_api, "localhost:8001")


@pytest.fixture()
def sms_client(sms_application):
    return sms_application.test_client()


@pytest.fixture()
def mobile_api_client(mobile_api_app):
    return mobile_api_app.test_client()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def set_up_db():
    DatabaseSeeder.create_db()
    DatabaseSeeder.init_default_data()


@pytest.fixture
def super_admin_app(client):
    return login(client,
                 dict(username="super_admin@test.com", password="test1234"))


@pytest.fixture
def admin_app(client):
    return login(client, dict(username="admin@test.com", password="test1234"))


@pytest.fixture
def agent_app(client):
    return login(client, dict(username="agent@test.com", password="test1234"))


@pytest.fixture
def manager_app(client):
    return login(client, dict(username="manager@test.com", password="test1234"))


@pytest.fixture
def view_only_app(client):
    return login(client, dict(username="view_only@test.com", password="test1234"))


@pytest.fixture
def incorrect_login(client):
    return login(client,
                 dict(username="nonexistent_user@test.com", password="test1234"))


@pytest.fixture()
def templates(app):
    return captured_templates(app)


@pytest.fixture
def context():
    return web_app.app_context()


@pytest.fixture()
def sms_context():
    return api_app.test_request_context()


@pytest.fixture()
def mobile_api_context():
    return mobile_api.test_request_context()


@pytest.fixture()
def sms_templates():
    return captured_templates(api_app)


@pytest.fixture
def apps(super_admin_app,
         admin_app,
         agent_app,
         manager_app,
         view_only_app,
         incorrect_login,
         client):

    return {
        'SuperAdmin': super_admin_app,
        'Admin': admin_app,
        'Manager': manager_app,
        'Agent': agent_app,
        'ViewOnly': view_only_app,
        'NotLoggedIn': client
    }


def login(app, params):
    app.post(
       '/login/?next=/settings',
       data=params,
       follow_redirects=False)
    return app


@pytest.fixture
def api_client(request):
    api_app.testing = True
    config.ALLOWED_HOOKS += ['test_event']
    test_client = api_app.test_client()

    def teardown():
        pass # databases and resources have to be freed at the end. But so far we don't have anything

    request.addfinalizer(teardown)
    return test_client

@pytest.fixture
# @db_session
def super_admin_user():
    return lambda: db.User.get(username="super_admin@test.com")

@pytest.fixture
# @db_session
def admin_user():
    return lambda: db.User.get(username="admin@test.com")

@pytest.fixture
def good_api_key():
    good_permission_dict = ['TestPermission', 'TestPostPermission',
                            'AddAPIHook', 'DeleteAPIHook', 'ViewClients',
                            'AddOutgoingMessages',
                            'AddIncomingMessages', 'ViewMessages',
                            'AddPayments', 'AddReversedPayments',
                            'ViewInteractions', 'AddInteractions',
                            'DeleteInteractions',
                            'ViewForms', 'AddForms',
                            'EditForms']
    return generate_jwt(1, good_permission_dict, 'Solaris Offgrid',
                 config.api_secret,
                 expiration_time=datetime.now() + timedelta(days=1))

@pytest.fixture
def gateway_api_key():
    good_permission_dict = ['TestPermission', 'TestPostPermission',
                            'AddAPIHook', 'DeleteAPIHook', 'ViewClients',
                            'AddOutgoingMessages',
                            'AddIncomingMessages', 'ViewMessages',
                            'AddPayments', 'AddReversedPayments',
                            'ViewInteractions', 'AddInteractions',
                            'DeleteInteractions',
                            'ViewForms', 'AddForms',
                            'EditForms']
    return generate_jwt(0, good_permission_dict, 'Solaris Offgrid',
                 config.api_secret,
                 expiration_time=datetime.now() + timedelta(days=1))

@pytest.fixture
@db_session
def admin_api_key():
    good_permission_dict = generate_permission_list_from_dict(all_permissions)
    return generate_jwt(db.User.get(username="super_admin@test.com").id, good_permission_dict, 'Solaris Offgrid',
                        config.api_secret,
                        expiration_time=datetime.now() + timedelta(days=1))

@pytest.fixture
def expired_api_key():
    return generate_jwt(1, ['TestPermission', 'TestPostPermission'], 'Solaris Offgrid',
                        config.api_secret,
                        expiration_time=datetime.now() + timedelta(days=-1))

@pytest.fixture
@db_session
def api_key_bad_permissions():
    return generate_jwt(db.User.get(username="view_only@test.com").id, ['Wrong'], 'Solaris Offgrid',
                        config.api_secret,
                        expiration_time=datetime.now() + timedelta(days=1))
