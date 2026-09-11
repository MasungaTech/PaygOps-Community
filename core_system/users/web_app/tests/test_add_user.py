from core_system.operational_entities.models import Hub
from tests.base_test import BaseTestMethods
from flask import url_for
from pony.orm import db_session, flush
from urllib.parse import urlparse
from core_system.role.methods.getters import get_role_from_name
from core_system.users.models.user_model import User
from accounting_system.accounting_db import AccountingUser


class TestUserAdd:
    def get(self, app):
        return app.get(url_for("user.add_user"))

    @db_session
    def test_not_logged_in_returns_302(self, client, context):
        with context:
            response = self.get(client)
            assert 302 == response.status_code
            assert urlparse(url_for("login.login")).path == response.location.split('?')[0]

    @db_session
    def test_view_only_user_with_permission_returns_200(self, view_only_app, context):
        with context:
            response = self.get(view_only_app)
            assert response.status_code == 302
            assert urlparse(url_for("index")).path == response.location.split('?')[0]

    @db_session
    def test_super_admin_should_return_200_and_have_a_template(self, templates, context, super_admin_app):
        with templates as tmpl, context:
            rv = self.get(super_admin_app)
            assert rv.status_code == 200
            assert len(tmpl) == 1
            template, context = tmpl[0]

            assert template.name == 'edit_user.html'
            assert len(list(context['Shops'])) > 0

