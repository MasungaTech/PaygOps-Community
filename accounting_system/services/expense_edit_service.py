from datetime import datetime
import json
from accounting_system.accounting_db import Account, Expense
import config

from shared.helpers.date_helper import parse_datetime
from shared.logger.loggers import Error
from accounting_system.accounting_interface import getCurrentUserById
from shared.services.base_service import BaseService


class ExpenseEditService(BaseService):

    @classmethod
    def _delete_from_object_and_user(cls, expense, user):
        expense.delete()

    @classmethod
    def _get_expense_account_from_data(cls, data, user, strict=False):
        account = data.get('account')
        user_id = data.get('user_id')
        currentAccountingUser = getCurrentUserById(user.id)
        if account:
            expenseAccount = Account.get(id=int(account))
        elif user_id:
            expenseAccount = Account.select().filter(lambda a: a.owner.webUserID == user_id).first()
        elif not strict:
            expenseAccount = currentAccountingUser.getFirstAccount()
        if not user.can_access('EditOthersExpenses'):
                if (not account.owner) or account.owner.getWebUser() != user:
                    raise Error('INSUFFICIENT_PERMISSION', permission='EditOthersExpenses')
        return expenseAccount

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        user = user.reload()
        currentAccountingUser = getCurrentUserById(user.id)

        expense_date_str = data.get('date')
        if not expense_date_str:
            raise Error('Expense date is required')
        expense_date = parse_datetime(expense_date_str) 
        amount = data.get('amount')
        if not amount:
            raise Error('Amount is required')
        description = data.get('description')
        if not description:
            raise Error('Description is required')
        receiptPicture = data.get('receipt_picture', '')
        if not receiptPicture and config.ExpenseReceiptCompulsory:
            raise Error('Receipt picture is required')
        category = data.get('category')
        if not category:
            raise Error('Expense category is required')
        else:
            expenseType = category

        if expenseType == 'Fuel':
            additionalData = json.dumps(data.get('additional_data'))
        else:
            additionalData=''

        expenseAccount = cls._get_expense_account_from_data(data, user)
        if not expenseAccount:
            raise Error('Expense account is required')

        associatedTransfer = None
        reportedBy = currentAccountingUser
        receiptType = data.get('receipt_type')
        supportingDoc1 = data.get('supporting_document_1', '')
        supportingDoc1Type = data.get('supporting_document_1_type')
        supportingDoc2 = data.get('supporting_document_2','')
        supportingDoc2Type = data.get('supporting_document_2_type')
        supportingDoc3 = data.get('supporting_document_3','')
        supportingDoc3Type = data.get('supporting_document_3_type')
        thisExpense =  cls.add_expense(expense_date=expense_date, amount=amount, category=expenseType, description=description, additionalData=additionalData,
                                receiptPicture=receiptPicture, account=expenseAccount,receiptType=receiptType, reportedBy=reportedBy,
                                associatedTransfer=associatedTransfer, supportingDoc1=supportingDoc1, supportingDoc1Type=supportingDoc1Type,
                                supportingDoc2=supportingDoc2, supportingDoc2Type=supportingDoc2Type, supportingDoc3=supportingDoc3, supportingDoc3Type=supportingDoc3Type)
        return thisExpense

    @classmethod
    def _edit_from_data_and_user(cls, this_expense, data, user):

        return cls.edit_expense(this_expense, data, user)

    @classmethod
    def edit_expense(cls, thisExpense, data, user):
        if not user.can_access('EditOthersExpenses'):
            if (not thisExpense.getUserPaying() or thisExpense.getUserPaying().getWebUser() != user):
                raise Error('INSUFFICIENT_PERMISSION', permission='EditOthersExpenses')
        
        timeSinceEntry = (datetime.now() - thisExpense.entryDate).seconds / 3600
        if 'description' in data:
            thisExpense.description = data.get('description')
        if 'amount' in data:
            OldAmount = thisExpense.amount
            NewAmount = float(data['amount'])
            if OldAmount != NewAmount:
                if not user.can_access('EditAmountExpenses') and timeSinceEntry > 24:
                    raise Error('You do not have the permission to edit accounting amount.')
                else:
                    thisExpense.amount = NewAmount
        if 'category' in data:
            thisExpense.category = data.get('category')
        if thisExpense.category == 'Fuel':
            thisExpense.additionalData = json.dumps(data.get('additional_data'))
        else:
            thisExpense.additionalData = ''
        if 'receipt_picture' in data:
            thisExpense.receiptPicture = data.get('receipt_picture')
        if 'receipt_type' in data:
            thisExpense.receiptType = data.get('receipt_type')
        if 'account' in data or 'user_id' in data:
            thisExpense.account = cls._get_expense_account_from_data(data, user, strict=True)
        if 'supporting_document_1' in data:
            thisExpense.supportingDoc1 = data.get('supporting_document_1')
        if 'supporting_document_1_type' in data:
            thisExpense.supportingDoc1Type = data.get('supporting_document_1_type')
        if 'supporting_document_2' in data:
            thisExpense.supportingDoc2 = data.get('supporting_document_2')
        if 'supporting_document_2_type' in data:
            thisExpense.supportingDoc2Type = data.get('supporting_document_2_type')
        if 'supporting_document_3' in data:
            thisExpense.supportingDoc3 = data.get('supporting_document_3')
        if 'supporting_document_3_type' in data:
            thisExpense.supportingDoc3Type = data.get('supporting_document_3_type')
        if 'date' in data:
            expense_date = parse_datetime(data.get('date')) 
            thisExpense.date = expense_date
        return thisExpense


    @classmethod
    def add_expense(cls, expense_date, amount, category, description, additionalData, receiptPicture, receiptType, account, reportedBy, associatedTransfer,supportingDoc1, supportingDoc1Type, supportingDoc2, supportingDoc2Type, supportingDoc3, supportingDoc3Type):
        this_expense = Expense(
            date = expense_date,
            entryDate = datetime.now(),
            amount = amount,
            category = category,
            description = description,
            additionalData = additionalData,
            receiptPicture = receiptPicture,
            receiptType = receiptType,
            account = account,
            reportedBy = reportedBy,
            associatedTransfer = associatedTransfer,
            supportingDoc1 = supportingDoc1,
            supportingDoc1Type = supportingDoc1Type,
            supportingDoc2 = supportingDoc2,
            supportingDoc2Type = supportingDoc2Type,
            supportingDoc3 = supportingDoc3, 
            supportingDoc3Type = supportingDoc3Type
        )
        return this_expense