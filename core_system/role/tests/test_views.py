import pytest
import json
from pony import orm
from tests.base_test import BaseViewTest
from core_system.role.models import Role


class TestEditRoleView(BaseViewTest):
    url = 'permissions.edit_role'
    template = 'edit_role.html'

    @classmethod
    @pytest.fixture(autouse=True)
    @orm.db_session
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.role = Role.select().first()
        cls.params = dict(role_id=cls.role.id)

class TestCreateRoleView(BaseViewTest):
    url = 'permissions.create_role'
    template = 'edit_role.html'

    @classmethod
    @pytest.fixture(autouse=True)
    @orm.db_session
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
