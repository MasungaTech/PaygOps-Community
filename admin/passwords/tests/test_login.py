import pytest

from pony.orm import db_session
from flask import url_for

from tests.base_test import BaseTestMethods
from sales_system.lead_generator.model import LeadGenerator


class TestLoginView(BaseTestMethods):
    url = 'login.login'
    template = 'login.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates

    
    def test_not_logged_in_returns_200(self, client):
        response = self.get(client)

        assert 200 == response.status_code
        assert response.template_is(self.template)

    def test_login_success(self, client):
        with db_session:
            resp = self.post(client, dict(username="admin@test.com", password="test1234"))

        assert resp.status_code == 200
        assert b'Login Successful' in resp.data
        assert resp.template_is('overview.html')

    def test_login_unsucessful(self, client):
        resp = self.post(client, dict(username="nonexistent_user@test.com", password="test1234"))
        assert resp.status_code == 200
        assert b'Login Unsuccessful' in resp.data
