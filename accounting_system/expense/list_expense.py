from werkzeug.exceptions import NotFound
from accounting_system.services.account_getter_service import AccountGetterService
from os import O_WRONLY
from accounting_system.services.expense_getter_service import ExpenseGetterService
from flask import request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from shared.helpers.authorizer import authorizer
from pony.orm import db_session

from accounting_system.accounting_interface import getCurrentUser,\
    getAllExpenses, getCurrentUserById
from accounting_system.accounting_db import Account, Expense
from shared.helpers.pagination import Pagination
from . import expense


@expense.route('/', methods=['GET'])
@login_required
@authorizer('ViewExpenses')
@db_session
def list_expense():
    pagination = Pagination.generate(request, tab='expenses', default_sort='date:desc')
    expenses = ExpenseGetterService.get_list(current_user)
    pagination.objects = Expense.sort(expenses, pagination.sort)
    return render_template('list_expense.html', pagination=pagination)


@expense.route('/user/<int:user_id>', methods=['GET'])
@login_required
@db_session
def list_expense_by_user(user_id):
    pagination = Pagination.generate(request, tab='expenses')

    if user_id:
        currentAccountingUser = getCurrentUserById(user_id)
        if not currentAccountingUser:
            flash('Invalid User ID. ')
            return redirect(url_for('.list_expense'))
    else:
        currentAccountingUser = getCurrentUser()

    expenses = ExpenseGetterService.get_list(current_user, owner=currentAccountingUser)
    pagination.objects = Expense.sort(expenses, pagination.sort)

    return render_template('list_expense.html', pagination=pagination)


@expense.route('/account/<int:account_id>', methods=['GET'])
@login_required
@authorizer('ViewExpenses')
@db_session
def list_expense_by_account(account_id):
    account = AccountGetterService.get_from_user_and_id(current_user, account_id, strict=True, main_resource=True)

    pagination = Pagination.generate(request, tab='expenses')
    expenses = account.getExpenses()
    pagination.objects = Expense.sort(expenses, pagination.sort)

    return render_template('list_expense.html', pagination=pagination)
