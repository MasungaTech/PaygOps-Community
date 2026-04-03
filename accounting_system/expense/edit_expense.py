from accounting_system.services.account_getter_service import AccountGetterService
from collections import OrderedDict
from flask import request, flash, redirect, url_for, render_template
from accounting_system.services.expense_edit_service import ExpenseEditService
from core_system.users.services.user_getter_service import UserGetterService
from flask_login import login_required, current_user
from shared.helpers.authorizer import authorizer
from shared.helpers.select2 import render
from pony.orm import db_session, commit, rollback
from datetime import datetime
import json

import config

from accounting_system.accounting_db import Account, ExpenseReceiptTypes, getExpenseReceiptTypeName, Expense
from accounting_system.services.expense_getter_service import ExpenseGetterService
from config import DEPARTMENT_LIST, MAIN_EXPENSE_CATEGORIES, ADDITIONAL_EXPENSE_CATEGORIES, ALL_EXPENSE_CATEGORIES
from data_system.services.store_file_service import store_file
from shared.helpers.db_helpers import getMemberVariables
from shared.helpers.picture_helper import picture_uploaded

from . import expense


def get_receipt_types():
    types = OrderedDict()
    for type in sorted(getMemberVariables(ExpenseReceiptTypes)):
        types[type] = getExpenseReceiptTypeName(type)
    return types


@expense.route('/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
@authorizer('EditExpenses')
@db_session
def edit_expense(expense_id):
    thisExpense = ExpenseGetterService.get_from_user_and_id(current_user, expense_id)
    if not thisExpense:
        flash('This expense does not exist')
        return redirect(url_for('expense.list_expense'))
    
    if not current_user.can_access('EditOthersExpenses') and (not thisExpense.getUserPaying() or thisExpense.getUserPaying().getWebUser() != current_user):
        flash('You do not have the permission to edit this expense')
        return redirect(url_for('expense.list_expense'))

    ALL_EXPENSE_CATEGORIES.sort()
    users = UserGetterService.get_list(current_user.reload())
    if not current_user.can_access('EditOthersExpenses'):
        users = users.filter(lambda u: u.id == current_user.id)
    select2 = {
            'user_accounts': {    
                'items': users,
                'selected': thisExpense.account.id if thisExpense else '',
                'text': 'full_name',
            },
        }
    return render('edit_expense.html', select2=select2, Expense=thisExpense, 
                    receipt_types=get_receipt_types(),
                    ALL_EXPENSE_CATEGORIES=ALL_EXPENSE_CATEGORIES)


@expense.route('/add', methods=['GET'])
@login_required
@authorizer('AddExpenses', 'list_expense')
@db_session
def add_expense():

    ALL_EXPENSE_CATEGORIES.sort()
    users = UserGetterService.get_list(current_user.reload())
    selected = None
    if not current_user.can_access('EditOthersExpenses'):
        users = users.filter(lambda u: u.id == current_user.id)
        selected = current_user
    select2 = {
        'user_accounts': {
            'items': users,
            'text': 'full_name',
            'selected': selected
        },
    }
    return render('edit_expense.html', select2=select2,
                    ALL_EXPENSE_CATEGORIES=ALL_EXPENSE_CATEGORIES,
                    receipt_types=get_receipt_types())
