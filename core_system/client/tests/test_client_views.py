import json
from shared.helpers.client_creator import ClientCreator
import pytest
from datetime import datetime
from pony.orm import db_session, commit
from tests.base_test import BaseViewTest, BaseViewJsonTest, \
    PermissionBaseTest, BaseTestMethods
from core_system.client.models import Client
from core_system.person.models.person_model import Person
from core_system.operational_entities.models import Village


def get_client():
    return Client.select().first()

class TestListClientView(BaseViewTest):
    url = 'client.list_client'
    template = 'list_client.html'

    @pytest.mark.xfail(reason='This calls the child context of client list element')
    @db_session
    def test_context_contains_pagination(self, super_admin_app):
        response = self.get(super_admin_app, self.url)

        assert response.context.get('pagination', None)


class TestEditClientView(BaseViewTest):
    url = 'client.edit_client'
    template = 'edit_client.html'

    @classmethod
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        with db_session:
            cls.entrepreneur = get_client()
            cls.params = dict(client_id=cls.entrepreneur.id)

    @db_session
    def test_view_only_user_with_permission_returns_200(self, super_admin_app):
        response = self.get(super_admin_app)

        assert 200 == response.status_code
        assert response.template_is(self.template)


class TestViewClientView(BaseViewTest):
    url = 'client.view_client'
    template = 'view_client.html'

    @classmethod
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        with db_session:
            cls.client = get_client()
            cls.params = dict(client_id=cls.client.id)

    @db_session
    def test_redirect_if_not_exist(self, super_admin_app):
        self.params = dict(client_id=0)
        response = self.get(super_admin_app, params=dict(client_id=0))
        assert b'Redirecting' in response.data


class TestViewClientMap(BaseViewTest):

    @pytest.fixture(autouse=True)
    def setup_method(self, templates, context):
        if hasattr(self, "set_params"):
            self.set_params()
        self.context = context
        self.templates = templates
        with db_session:
            client = get_client()
            client.person.GPSLon = 2.2
            client.person.GPSLat = 2.2
            commit()

    url = 'client.clients_map'
    template = 'clients_map.html'


class TestListClientPermissions(PermissionBaseTest):
    url = 'client.list_client'
    allowed_roles = ['SuperAdmin', 'Admin', 'Agent', 'ViewOnly']
    not_allowed_roles = []


class ClientEndpointTestMethods(BaseTestMethods):
    allowed_methods = ['POST']

    @classmethod
    @db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.entrepreneur = get_client()
        cls.params = dict(client_id=cls.entrepreneur.id)


