import pytest
from accounting_system.accounting_db import Account
from accounting_system.services.account_getter_service import AccountGetterService
from accounting_system.services.expense_edit_service import ExpenseEditService
from core_system.users.models.user_model import User
from tests.base_test import BaseViewTest, BaseTestMethods
from pony.orm import db_session
from datetime import datetime


class TestListExpense(BaseViewTest):
    url = 'expense.list_expense'
    template = 'list_expense.html'


class TestListExpenseByUser(BaseViewTest):
    url = 'expense.list_expense_by_user'
    template = 'list_expense.html'
    params = dict(user_id=1)


class TestListExpenseByAccount(BaseViewTest):
    url = 'expense.list_expense_by_account'
    template = 'list_expense.html'

    @classmethod
    @pytest.fixture(autouse=True)
    @db_session
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        user = User.get(username="super_admin@test.com")
        cls.params = dict(account_id=AccountGetterService.get_list(user).first().id)
        new_expense = ExpenseEditService.add_from_data_and_user({
            'date': datetime.now().isoformat(),
            'amount': 123,
            'description': 'test expense',
            'receipt_picture': '111-222',
            'category': 'Travel Expense'
        }, user)


    @db_session
    def test_returns_404(self, super_admin_app):
        self.params = {'account_id': 0}
        response = self.get(super_admin_app)
        assert 404 == response.status_code


class TestAddExpense(BaseViewTest):
    url = 'expense.add_expense'
    template = 'edit_expense.html'

class TestEditExpense(BaseViewTest):
    url = 'expense.edit_expense'
    template = 'edit_expense.html'
    params = dict(expense_id=1)


class TestViewExpense(BaseViewTest):
    url = 'expense.view_expense'
    template = 'view_expense.html'
    params = dict(expense_id=1)
