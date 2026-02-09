from urllib.parse import urlparse
from flask import url_for
from pony.orm import *


class TestUserList:
    def get(self, app):
        return app.get(url_for("user.list_users"))

    def test_not_logged_in_returns_302(self, client, context):
        with context:
            response = self.get(client)
            assert 302 == response.status_code
            assert urlparse(url_for("login.login")).path == response.location.split('?')[0]

    @db_session
    def test_view_only_user_with_permission_returns_200(self,
                                                        super_admin_app,
                                                        context):
        with context:
            response = self.get(super_admin_app)
            assert response.status_code == 200

    @db_session
    def test_super_admin_should_return_200_and_have_a_template(self, templates, context, super_admin_app):
        with templates as tmpl, context:
            rv = self.get(super_admin_app)
            assert rv.status_code == 200
            assert len(tmpl) == 1
            template, context = tmpl[0]

            assert template.name == 'list_users.html'
