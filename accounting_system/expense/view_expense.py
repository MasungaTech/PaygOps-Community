import os
from flask import flash, redirect, url_for, render_template, send_file
from flask_login import login_required
from shared.helpers.authorizer import authorizer
from pony.orm import db_session

from accounting_system.accounting_interface import getExpenseByID
from . import expense
from config import CURRENT_DIR, RECEIPT_PICTURES_PATH


@expense.route('/<int:expense_id>', methods=['GET'])
@login_required
@authorizer('ViewExpenses')
@db_session
def view_expense(expense_id):

    thisExpense = getExpenseByID(expense_id)

    if thisExpense is None:
        flash("Invalid Expense ID. ")
        return redirect(url_for('.list_expense'))

    return render_template('view_expense.html', Expense=thisExpense)


@expense.route('/receipts/<int:receipt_id>')
@login_required
def send_receipt(receipt_id):
    picture_filename = str(receipt_id)
    picture_fullpath = os.path.join(RECEIPT_PICTURES_PATH, picture_filename)
    if os.path.isfile(picture_fullpath):
        return send_file(picture_fullpath)
    else:
        nopic = CURRENT_DIR+'/web_app/static/img/missing_receipt.png'
        return send_file(nopic)


@expense.route('/receipts/small/<int:receipt_id>')
@login_required
def send_receipt_small(receipt_id):
    picture_filename = str(receipt_id)
    picture_fullpath = os.path.join(RECEIPT_PICTURES_PATH + 'small/', picture_filename)
    if os.path.isfile(picture_fullpath):
        return send_file(picture_fullpath)
    else:
        nopic = CURRENT_DIR+'/web_app/static/img/missing_receipt.png'
        return send_file(nopic)
