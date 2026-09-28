import pytest
import json
from pony import orm
from tests.base_test import BaseViewTest
from core_system.role.models import Role


class TestEditRoleView(BaseViewTest):
    url = 'permissions.edit_role'
    template = 'edit_role.html'

    @pytest.fixture(autouse=True)
    @orm.db_session
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.role = Role.select().first()
        self.params = dict(role_id=self.role.id)

class TestCreateRoleView(BaseViewTest):
    url = 'permissions.create_role'
    template = 'edit_role.html'

    @pytest.fixture(autouse=True)
    @orm.db_session
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
