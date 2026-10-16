from accounting_system.accounting_db import Account
from shared.services.base_getter_service import BaseGetterService


class AccountGetterService(BaseGetterService):

    OBJ_NAME = 'Account'

    @classmethod
    def get_filtered_objects(cls, current_user, managed_by=None, requester=None, **kwargs):
        accounts = Account.select()
        if not current_user.can_access('ViewAccounts'):
            return accounts.filter(id=-1)
        if not current_user.can_access('ManageAllAccounts'):
            if managed_by:
                if not current_user.can_access('ManageAccounts'):
                    return accounts.filter(id=-1)
                accounting_user = managed_by.accounting_user()
                accounts = accounts.filter(lambda a: a.owner == accounting_user or accounting_user in a.managers)
            if requester:
                accounting_user = requester.accounting_user()
                accounts = accounts.filter(lambda a: accounting_user in a.requesters or accounting_user in a.managers)
        return accounts
