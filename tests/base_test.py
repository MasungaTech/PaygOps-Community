from urllib.parse import urlparse
from datetime import datetime
import json
import pytest
import config

if not config.ENABLE_ENTERPRISE_FEATURES:
    pytest.skip("Enterprise-only tests that rely on after_sales_system are disabled for OSS builds.", allow_module_level=True)

from after_sales_system.issue_system.services.issue_service import IssueService
from payg_loan_system.offers.models import Offer
from payg_loan_system.contracts.services.tests.factories import TestContractCreator
from munch import Munch
from core_system.client.models import Client
from core_system.users.models.user_model import User
from after_sales_system.interaction_system.model.interaction_report_model import DiscussedTopic, InteractionReport, InteractionTopic

from flask import url_for
from pony.orm import db_session
from core_system.role.methods.setters import edit_role_from_form
from core_system.role.methods.getters import (get_role_from_name,
                                              get_permission_objects_from_list_of_names,
                                              get_all_permissions)

@db_session
def add_issue():
    contract = TestContractCreator.create_test_contract(
        'Test Contract '+str(Client.select().count()+1),
        offer=Offer.select(lambda o: o.code != 'TDO').first()
    )
    params = dict(client=contract.client.id,
                  type=1,
                  priority=3,
                  method=1)
    params = json.dumps(params)
    user = get_user()

    return addQuickIssueFromJSON(params, user)

def addQuickIssueFromJSON(receivedJSON, user):
    data = Munch(json.loads(receivedJSON))

    thisClient = Client.get(id=data.client)
    thisUser = User.get(id=user.id)
    thisTopic = InteractionTopic.get(name='Reporting new Issue')

    thisIssue = IssueService.add_from_data_and_user({
        'affected_client_id': thisClient.id,
        'priority': int(data.priority),
        'type_id': data.type
    }, thisUser)

    thisInteraction = InteractionReport(reportDate=datetime.now(),
                                   entryDate=datetime.now(),
                                   method=data.method,
                                   clientInitiated=True,
                                   client=thisClient,
                                   userReporting=thisUser,
                                   mainTopic=thisTopic)


    # TODO: Add the discussion support
    thisDiscussion = DiscussedTopic(interaction=thisInteraction,
                                    topic=thisTopic,
                                    discussedIssue=thisIssue)

    return thisIssue

def get_user():
    return User.select().first()

class PermissionBaseTest:
    params = {}
    url = ''
    not_allowed_roles = []
    allowed_roles = []

    @pytest.fixture(autouse=True)
    def setup_method(cls, context):
        add_issue()
        cls.context = context

    def get(self, app, params={}, redir=False):
        with self.context:
            response = app.get(url_for(self.url, **self.params),
                               follow_redirects=redir)

            return ViewResponse(response,
                                app_context=self.context)

    @db_session
    def test_allowed_permissions(self, apps):
        for role in self.allowed_roles:
            app = apps.get(role)

            if app:
                res = self.get(app, self.url)
                print(role)
                print(res.status_code)
                print(res.data)
                assert res.status_code == 200
            else:
                assert False

    @db_session
    def test_not_allowed_permissions(self, apps):
        for role in self.not_allowed_roles:
            app = apps.get(role)

            if app:
                res = self.get(app, self.url)
                print(role)
                print(res.status_code)
                print(res.data)
                assert res.status_code == 302 or b"You don't have the proper" in res.data
            else:
                assert False


class BaseTestMethods:
    params = {}
    allowed_methods = ['GET']

    @pytest.fixture(autouse=True)
    def setup_method(self, templates, context):
        if hasattr(self, "set_params"):
            self.set_params()
        self.context = context
        self.templates = templates

    def get(self, app, params=params, query_str=None, follow_redirects=False):
        template = None
        context = None
        newparams = params if params else self.params
        with self.templates as tpl, self.context:
            response = app.get(url_for(self.url, **newparams), query_string=query_str, follow_redirects=follow_redirects)

            if len(tpl) > 0:
                template, context = tpl[0]

            return ViewResponse(
                response,
                template=template,
                context=context,
                app_context=self.context)

    def post(self, app, data, redir=True, **kwargs):
        template = None
        context = None

        with self.templates as tpl, self.context:
            print(url_for(self.url, **self.params))
            response = app.post(url_for(self.url, **self.params),
                                data=data,
                                follow_redirects=redir,
                                **kwargs)

            if len(tpl) > 0:
                template, context = tpl[0]

            return ViewResponse(
                response,
                template=template,
                context=context,
                app_context=self.context)

class BaseViewTest(BaseTestMethods):

    redirect = False

    def test_user_with_permission_returns_200(self, super_admin_app):
        if 'GET' in self.allowed_methods:
            response = self.get(super_admin_app, follow_redirects=self.redirect)
            print('status', response.status_code)
            assert response.status_code == 200
            assert response.template_is(self.template)

    def test_not_logged_in_returns_302(self, client):
        if 'GET' in self.allowed_methods:
            response = self.get(client)
            assert 302 == response.status_code
            print(response.response.__dict__)
            assert response.location_is('login.login')


class BaseViewJsonTest:
    params = {}

    @pytest.fixture(autouse=True)
    def setup_method(cls, context):
        cls.context = context

    def get(self, app, params={}):
        with self.context:
            response = app.get(url_for(self.url, **self.params))

            return JsonResponse(response, app_context=self.context)

    def post(self, app, data, redir=True, headers=None):
        with self.context:
            response = app.post(url_for(self.url, **self.params),
                                data=data,
                                follow_redirects=redir,
                                headers=headers)

            return JsonResponse(response, app_context=self.context)


class BaseSMSAppTest(BaseViewJsonTest):
    @pytest.fixture(autouse=True)
    def setup_method(cls, sms_context):
        cls.context = sms_context


class ViewResponse:
    def __init__(self, response, app_context, template=None, context=None):
        self.response = response
        self.context = context
        self.template = template
        self.app_context = app_context

    @property
    def status_code(self):
        return self.response.status_code

    @property
    def location(self):
        return self.response.location

    @property
    def data(self):
        return self.response.data

    def location_is(self, url, **kwargs):
        with self.app_context:
            expected_location = urlparse(url_for(url, **kwargs)).path
            actual_location = urlparse(self.response.location).path

            # Compare the paths of both URLs
            print('Expected Location:', expected_location)
            print('Actual Location:', actual_location)
            return expected_location == actual_location

    def template_is(self, name):
        return self.template.name == name


class JsonResponse(ViewResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def json_data(self):
        return json.loads(self.response.data.decode('utf-8'))
