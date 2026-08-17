from flask import url_for
import pytest
from pony.orm import db_session
from shared.api_helpers.api_structure import API_STRUCTURE
from shared.api_helpers.documented_resource import DocumentedResource

from tests.base_test import BaseViewTest, ViewResponse


class TestAdminMenu(BaseViewTest):
    url = 'admin.admin'
    template = 'admin.html'

    allowed_methods = ['GET', 'POST']


class TestSettingsPage(BaseViewTest):
    url = 'admin.user_settings'
    template = 'user_settings.html'

    allowed_methods = ['GET', 'POST']
    form = dict(action='change_pass',
                old_password='test1234',
                new_password='happ',
                new_password_confirm='happy')

    @db_session
    def test_change_password_not_equal(self, super_admin_app):

        res = self.post(super_admin_app, self.form)
        assert res.status_code == 200
        assert res.template_is('user_settings.html')
        assert b'The two passwords are different. Operation aborted.' in res.data

    @db_session
    def test_incorrect_old_password(self, super_admin_app):
        self.form['old_password'] = 'WRONG'
        res = self.post(super_admin_app, self.form)
        assert res.status_code == 200
        assert res.template_is('user_settings.html')
        assert b'Old password wrong!' in res.data

    @pytest.mark.skip(reason='This messes up authorization for other tests that use super_admin')
    @db_session
    def test_change_password(self, super_admin_app):
        self.form['old_password'] = 'test1234'
        self.form['new_password'] = 'happy'
        res = self.post(super_admin_app, self.form)
        assert res.status_code == 200
        assert res.template_is('user_settings.html')
        assert b'Pass saved.' in res.data

    

class TestAPICallerViews:

    url = 'admin.api_caller_docs'
    template = 'api_caller_docs.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        def available(r):
            return issubclass(r, DocumentedResource) and r.PUBLIC
        with db_session:
            resources_docs = [(resource, resource.docs_get_metadata()) for resource in API_STRUCTURE if available(resource)]

            params = []
            for (resource, docs) in resources_docs:
                for method in resource._methods:
                    if method == 'get' or not method in docs or docs[method].get('deprecated'): continue
                    params += [resource.__name__+"_"+method]
            self.params = params
            self.context = context
            self.templates = templates
    
    @db_session
    def test_get_all(self, super_admin_app):
        template = None
        context = None
        with self.templates as tpl, self.context:
            for action in self.params:
                print(action)
                response = super_admin_app.get(url_for(self.url, action=action), follow_redirects=False)

                if len(tpl) > 0:
                    template, context = tpl[0]

                ViewResponse(
                    response,
                    template=template,
                    context=context,
                    app_context=self.context
                )
