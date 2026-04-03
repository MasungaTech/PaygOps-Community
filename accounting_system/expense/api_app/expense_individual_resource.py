
from accounting_system.accounting_db import Expense
from accounting_system.services.expense_edit_service import ExpenseEditService
from accounting_system.services.expense_getter_service import ExpenseGetterService
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual


class ExpensesIndividualResource(BaseAPIResourceIndividual):

    GET_SERVICE = ExpenseGetterService
    EDIT_SERVICE = ExpenseEditService
    GET_PERMISSION = 'ViewExpenses'
    EDIT_PERMISSION = 'EditExpenses'
    DELETE_SERVICE = ExpenseEditService
    DELETE_PERMISSION = 'DeleteExpenses'
    MODEL = Expense
    OBJECT_NAME = 'Expense'
    TAG = 'Expenses'

