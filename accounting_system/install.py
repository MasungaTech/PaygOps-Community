from pony.orm import exists, db_session, commit
from accounting_system.accounting_db import Account
import config


@db_session
def createCompanyAccounts():
    # Make the MPESA, Bank, and department accounts
    for A in config.COMPANY_ACCOUNTS:
        if not exists(EA for EA in Account if EA.name == A):
            Account(name=A, type=1)
    commit()


@db_session
def createDepartmentAccounts():
    for D in config.DEPARTMENT_LIST:
        if not exists(EA for EA in Account if EA.name == D+' Dept.'):
            Account(name=D+' Dept.', type=1)
    commit()
