import factory
from datetime import datetime
from accounting_system.accounting_db import Account, AccountingUser, Transfer


class AccountFactory(factory.Factory):
    class Meta:
        model = Account

    name = factory.Sequence(lambda n: 'ACCOUNT%d' % n)
    type = 1


class AccountingUserFactory(factory.Factory):
    class Meta:
        model = AccountingUser

    webUserID = factory.Sequence(lambda n: n * 10)


class TransferFactory(factory.Factory):
    class Meta:
        model = Transfer

    entryDate = datetime.today()
    requestDate = datetime.today()
    amount = 1000
    status = 1
    fromAccount = factory.SubFactory(AccountFactory)
    toAccount = factory.SubFactory(AccountFactory)
    requestBy = factory.SubFactory(AccountingUserFactory)
    requestAccount = factory.SubFactory(AccountFactory)
    approvedAccount = factory.SubFactory(AccountFactory)
