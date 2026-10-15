


from accounting_system.accounting_db import Expense
from accounting_system.services.account_getter_service import AccountGetterService
from shared.services.base_getter_service import BaseGetterService

class ExpenseGetterService(BaseGetterService):

    OBJ_NAME = 'Expense'

    @classmethod
    def get_filtered_objects(cls, current_user, owner=None, **kwargs):
        accounts = AccountGetterService.get_list(current_user)
        ids = [a.id for a in accounts]
        expenses = Expense.select(lambda e: e.account.id in ids)
        if owner:
            expenses = expenses.filter(lambda e: owner == e.account.owner)
        return expenses
