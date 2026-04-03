from tests.base_test import BaseViewTest
from pony import orm
import pytest
from sales_system.leads.models.lead import Lead


@orm.db_session
def get_lead():
    return Lead.select().first()

class TestLeadAddView(BaseViewTest):
    url = 'leads.add_lead'
    template = 'add_lead.html'


class TestLeadEditStatusView(BaseViewTest):
    url = 'leads.edit_lead_status'
    template = 'async_lead_views.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.lead = get_lead()
        cls.params = dict(lead_id=cls.lead.id)

class TestLeadEditGeneralInfoView(BaseViewTest):
    url = 'leads.edit_lead_general_info'
    template = 'async_lead_views.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.lead = get_lead()
        cls.params = dict(lead_id=cls.lead.id)

class TestLeadEditEntryView(BaseViewTest):
    url = 'leads.edit_lead_entry_info'
    template = 'async_lead_views.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.lead = get_lead()
        cls.params = dict(lead_id=cls.lead.id)

class TestListLeadsView(BaseViewTest):
    url = 'leads.list_lead'
    template = 'list_lead.html'

class TestListLeadsViewAll(BaseViewTest):
    url = 'leads.list_lead'
    template = 'list_lead.html'
    params = {'path': 'all'}

class TestListLeadsViewMe(BaseViewTest):
    url = 'leads.list_lead'
    template = 'list_lead.html'
    params = {'path': 'created'}

class TestListLeadsViewMyShop(BaseViewTest):
    url = 'leads.list_lead'
    template = 'list_lead.html'
    params = {'path': 'myshop'} 

class TestListLeadsViewMyCluster(BaseViewTest):
    url = 'leads.list_lead'
    template = 'list_lead.html'
    params = {'path': 'cluster'}

class TestViewEditView(BaseViewTest):
    url = 'leads.view_lead'
    template = 'view_lead.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.lead = get_lead()
        cls.params = dict(lead_id=cls.lead.id)

