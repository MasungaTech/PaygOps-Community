from core_system.operational_entities.models import Hub
from flask import url_for
from pony.orm import db_session
from urllib.parse import urlparse
from core_system.role.methods.getters import get_role_from_name


def route_rule(line):
    if line.startswith("http://localhost"):
        return line.split("http://localhost", 1).pop()
    return line


class TestUserUpdate:
    user_to_edit = dict(
        name="Test",
        surname="Name",
        username='new_user@test.com',
        hub_id=1,
        organization="SolarisOffgrid",
        phone_number='',
        phone_number_2='',
        login_expiration_date='',
        role_id='',
        password='test1234',
        password_confirm="test1234",
        pin=''
    )

    def get(self, app, id=None, redir=True):
        return app.get(url_for("user.edit_user", user_id=id), follow_redirects=redir)

    @db_session
    def post(self, app, params, id=None, redir=True):
        return app.post(url_for("user.edit_user", user_id=id),
                        data=params,
                        follow_redirects=redir)

    @db_session
    def test_super_admin_should_be_able_to_get_valid_user_to_edit(self, templates, context, super_admin_app):
        with templates as tmpl, context:
            self.user_to_edit['role_id'] = get_role_from_name('Agent').id
            rv = self.get(super_admin_app, id=1)
            assert rv.status_code == 200
            template, context = tmpl[0]
            assert template.name == 'edit_user.html'
            assert context['User']

    @db_session
    def test_super_admin_should_be_redirected_to_user_list_if_user_not_existent(self, context, super_admin_app):
        with context:
            self.user_to_edit['role_id'] = get_role_from_name('Agent').id
            rv = self.get(super_admin_app, id=10, redir=False)
            assert rv.status_code == 404

    @db_session
    def test_super_admin_should_be_able_to_edit_a_user(self, templates, context, super_admin_app):
        with templates as tmpl, context:
            self.user_to_edit['surname'] = 'Changed'
            self.user_to_edit['reference_entity_id'] = Hub.select().first().id
            rv = self.post(super_admin_app, self.user_to_edit, id=3)
            assert rv.status_code == 200
            assert b"edited" in rv.data
            template, context = tmpl[0]
            assert template.name == 'view_user.html'

    @db_session
    def test_user_with_mismatched_passwords_returns_and_error(self, templates, context, super_admin_app):
        with templates as tmpl, context:
            self.user_to_edit['password_confirm'] = 'test12345'

            rv = self.post(super_admin_app, self.user_to_edit, id=3)
            assert rv.status_code == 200
            template, context = tmpl[0]
            assert template.name == 'edit_user.html'
