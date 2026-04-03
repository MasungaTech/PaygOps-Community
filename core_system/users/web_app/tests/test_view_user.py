from flask import url_for
from pony.orm import db_session


class TestUserUpdate:
    user_to_view = dict(name="Test",
                        surname="Name",
                        username='new_user@test.com',
                        shop=1,
                        organization="SolarisOffgrid",
                        number1='',
                        number2='',
                        loginExpirationDate='',
                        auth_level='',
                        password='test1234',
                        password_confirm="test1234"
                        )

    def get(self, app, id=None, redir=True):
        return app.get(url_for("user.view_user", user_id=id), follow_redirects=redir)

    def post(self, app, params, id=None, redir=True):
        return app.post(url_for("user.view_user", user_id=id),
                        data=params,
                        follow_redirects=redir)

    @db_session
    def test_super_admin_should_be_able_to_view_user(self, templates, context, super_admin_app):
        with templates as tmpl, context:
            rv = self.get(super_admin_app, id=1)
            assert rv.status_code == 200
            template, context = tmpl[0]
            assert template.name == 'view_user.html'

    @db_session
    def test_agent_should_not_be_able_to_view_super_admin_user(self, templates, context, agent_app):
        with templates as tmpl, context:
            rv = self.get(agent_app, id=2)
            assert rv.status_code == 404

