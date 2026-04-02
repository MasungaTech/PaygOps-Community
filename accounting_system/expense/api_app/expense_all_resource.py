from accounting_system.accounting_db import Expense
from accounting_system.services.expense_getter_service import ExpenseGetterService
from accounting_system.services.expense_edit_service import ExpenseEditService
from constants import INTEGER_OPTIONAL_OPTIONS, INTEGER_OPTIONAL_OPTIONS_STRING
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll


class ExpensesAllResource(BaseAPIResourceAll):

    LIST_SERVICE = ExpenseGetterService
    ADD_SERVICE = ExpenseEditService
    LIST_PERMISSION = 'ViewExpenses'
    ADD_PERMISSION = 'AddExpenses'
    MODEL = Expense
    TAG = 'Expenses'

    EXTRA_LIST_PARAMS = {}

