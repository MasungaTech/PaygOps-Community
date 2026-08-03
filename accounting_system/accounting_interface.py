from datetime import datetime, timedelta
from flask_login import current_user
from pony.orm import select
from accounting_system.accounting_db import AccountingUser, Expense,\
    Transfer, TransferStatus


def createAccountingUserFromWebUser(webUser):
    return AccountingUser(webUserID=webUser.id)


def getCurrentUser():
    return select(
        U for U in AccountingUser if U.webUserID == current_user.id).first()


def getCurrentUserById(user_id):
    return select(
        U for U in AccountingUser if U.webUserID == user_id).first()


def getAllExpenses():
    return select(E for E in Expense)


def getExpenseByID(expenseID):
    return select(E for E in Expense if E.id == expenseID).first()


def getAllTransferRequests():
    return select(T for T in Transfer if T.status != TransferStatus.made)
