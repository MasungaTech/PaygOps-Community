from tests.base_test import BaseViewTest
import pytest
from pony.orm import db_session
from sales_system.lead_generator.model import LeadGenerator
import json


@db_session
def get_lead_generator(l_id=1):
    return LeadGenerator.get(id=l_id)


class TestViewLeadGeneratorView(BaseViewTest):

    url = 'lead_generator.view_lead_generator'
    template = 'view_lead_generator.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.lead_generator = get_lead_generator()
        self.params = dict(generator_id=self.lead_generator.id)

    @db_session
    def test_returns_404(self, super_admin_app):
        response = self.get(super_admin_app, params=dict(generator_id=0))
        assert 404 == response.status_code


class TestListLeadGeneratorView(BaseViewTest):
    url = 'lead_generator.list_lead_generator'
    template = 'list_lead_generator.html'


class TestEditLeadGeneratorEdit(BaseViewTest):
    url = 'lead_generator.edit_lead_generator'
    template = 'edit_lead_generator.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.lead_generator = get_lead_generator()
        self.params = dict(generator_id=self.lead_generator.id)

class TestAddLeadGeneratorView(BaseViewTest):
    url = 'lead_generator.add_lead_generator'
    template = 'edit_lead_generator.html'

