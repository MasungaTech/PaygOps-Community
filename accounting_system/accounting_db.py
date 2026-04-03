from decimal import Decimal
from datetime import datetime, timedelta
from pony.orm import *
from munch import Munch
import json

import config
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.model.interface import ModelInterface
from core_system.core_entities import db
from payg_loan_system.payments.models.wallet import PaymentWalletType


if config.TEST_MODE:
    accounting_db = Database("sqlite", ':memory:', create_db=True)
else:
    accounting_db = Database("postgres", user=config.PG_USER, password=config.PG_PASSWORD,
                             host=config.PG_HOST, port=config.PG_PORT, database=config.ACCOUNTING_DB_NAME)


class AccountingUser(accounting_db.Entity):
    webUserID = Required(int, unique=True) 
    mentorID = Optional(int, unique=True) # TO DO: remove
    department = Optional(str)

    expensesReported = Set("Expense", reverse="reportedBy")
    ownedAccounts = Optional("Account", reverse="owner")
    managedAccounts = Set("Account", reverse="managers")
    requestableAccounts = Set("Account", reverse="requesters")
    transfersRequested = Set("Transfer", reverse="requestBy")
    transfersDecided = Set("Transfer", reverse="decisionBy")
    transfersMade = Set("Transfer", reverse="madeBy")

    def getLink(self):
        this_user = self.getWebUser()
        if this_user is not None:
            return '<a href="/users/' + str(self.webUserID) + '">' + this_user.full_name + '</a>'
        else:
            return self.full_name

    def get_user_link(self):
        return '<a href = "/users/' + str(self.webUserID) + '">' + self.full_name + '</a>'

    def getWebUser(self):
        return db.User.get(id=self.webUserID)

    @property
    def full_name(self):
        return self.get_full_name()
    
    def get_full_name(self):
        thisUser = self.getWebUser()
        if thisUser is None:
            return 'UNKNOWN (' + str(self.id) + ')'
        else:
            return thisUser.full_name
    
    def createFirstAccount(self):
        newAccount = Account(owner=self, type=AccountType.employee)
        return newAccount

    def getFirstAccount(self):
        firstAccount = select(A for A in Account if A.owner == self).first()
        if firstAccount is None:
            return self.createFirstAccount(self)
        else:
            return firstAccount

    def get_expense_amount(self):
        return Decimal(select(E.amount for E in Expense if E.account.owner == self).sum())

    def get_net_transferred(self):
        transfers_from = select(T.amount for T in Transfer if T.fromAccount.owner == self if T.status == TransferStatus.made).sum()
        transfers_to = select(T.amount for T in Transfer if T.toAccount.owner == self if T.status == TransferStatus.made).sum()
        return Decimal(transfers_to-transfers_from) 


class AccountModelInterface(ModelInterface):
    @classmethod
    def of_company_type(cls):
        return select(A for A in cls if A.type == AccountType.company)


class Account(accounting_db.Entity, AccountModelInterface):
    name = Optional(str)
    type = Required(int)  # 0: Employee account, 1: Company Account
    owner = Optional(AccountingUser, reverse="ownedAccounts", column="owner")
    managers = Set(AccountingUser, reverse="managedAccounts")
    transfersSent = Set('Transfer')
    transfersReceived = Set('Transfer')
    expenses = Set('Expense')
    requesters = Set(AccountingUser, reverse='requestableAccounts')
    transferRequested = Set('Transfer', reverse='requestAccount')
    transferApproved = Set('Transfer', reverse='approvedAccount')

    def getLink(self):
        if self.owner is None:
            return '<a href="/accounting/accounts/' + str(self.id) + '">' + self.name + '</a>'
        else:
            return self.owner.getLink()

    def getName(self):
        if self.owner is None:
            return self.name
        else:
            return self.owner.full_name

    def isCompanyAccount(self):
        return (self.type == AccountType.company)

    def getPaymentsCollectedAmount(self, FromDate=None):
        PaymentsIn = 0
        if self.getName() == config.DEFAULT_PAYMENT_RECEPTION_ACCOUNT:
            if FromDate == None:
                PaymentsIn = select(P.Amount for P in db.Payment if P.PaymentWallet.Type == PaymentWalletType.mobile_money).sum()
            else:
                PaymentsIn = select(
                    P.Amount for P in db.Payment if P.PaymentWallet.Type == PaymentWalletType.mobile_money and P.PaymentTime > FromDate).sum()
        return Decimal(PaymentsIn)

    def get_expense_amount(self, FromDate=None):
        expense = 0

        if FromDate == None:
            expense = select(E.amount for E in Expense if E.account == self).sum()
        else:
            expense = select(E.amount for E in Expense if E.account == self and E.date > FromDate).sum()

        return Decimal(expense)

    def getExpenses(self):
        return select(E for E in Expense if E.account == self)

    def getTransfers(self):
        return select(
            T for T in Transfer if T.status == TransferStatus.made and (T.fromAccount == self or T.toAccount == self))

    def getPaymentsCollected(self, FromDate=None):
        PaymentsIn = select(P for P in db.Payment if False)  # Should not return anything
        if self.getName() == config.DEFAULT_PAYMENT_RECEPTION_ACCOUNT:
            if FromDate == None:
                PaymentsIn = select(P for P in db.Payment if P.PaymentWallet.Type == PaymentWalletType.mobile_money)
            else:
                PaymentsIn = select(P for P in db.Payment if P.PaymentWallet.Type == PaymentWalletType.mobile_money and P.PaymentTime > FromDate)
        return PaymentsIn


class AccountType():
    employee = 0
    company = 1


class Expense(accounting_db.Entity, ModelDefinitionMixin):
    date = Required(datetime)
    entryDate = Required(datetime)
    amount = Required(float)
    category = Optional(str, index=True)
    description = Optional(str)
    additionalData = Optional(str, lazy=True)
    department = Optional(str)
    receiptPicture = Optional(str)
    receiptType = Optional(int)
    account = Required(Account, column="account")
    reportedBy = Required(AccountingUser, reverse="expensesReported", column="reportedby")
    associatedTransfer = Optional('Transfer', reverse='usedForExpenses', column="associatedtransfer")
    supportingDoc1 = Optional(str)
    supportingDoc1Type = Optional(int)
    supportingDoc2 = Optional(str)
    supportingDoc2Type = Optional(int)
    supportingDoc3 = Optional(str)
    supportingDoc3Type = Optional(int)


    def getUserPaying(self):
        return self.account.owner

    def hasReceipt(self):
        return (self.receiptPicture != '')

    def getAdditionalData(self):
        if self.additionalData != '':
            additionalData = json.loads(self.additionalData)
            if additionalData:
                if 'LitresOfFuel' in additionalData:
                    additionalData['litres_of_fuel'] = additionalData.pop('LitresOfFuel')
                if 'Mileage' in additionalData:
                    additionalData['mileage'] = additionalData.pop('Mileage')
            return Munch().fromDict(additionalData)
        else:
            return Munch()

    def getReceiptTypeName(self, doc_number=None):
        if doc_number is None:
            return getExpenseReceiptTypeName(self.receiptType)
        elif doc_number == 1:
            return getExpenseReceiptTypeName(self.supportingDoc1Type)
        elif doc_number == 2:
            return getExpenseReceiptTypeName(self.supportingDoc2Type)
        elif doc_number == 3:
            return getExpenseReceiptTypeName(self.supportingDoc3Type)
        
    def get_link(self):
        from flask import url_for
        return url_for('expense.view_expense', expense_id=self.id)

    def get_display_id(self):
        return str(self.id)
        
    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "The ID of the expense",
                    "example": 12,
                    "value": lambda o: o.id
                },
                "date": {
                    "description": "This is the date when the expense was incurred",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.date
                },
                "entry_date": {
                    "description": "This is the date when the expense was recorded",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.date
                },
                "amount": {
                    "description": "The amount value of the expense",
                    "type": "number",
                    "example": 1234.56,
                    "value": lambda o: o.amount
                },
                "category": {
                    "description": "The category of the expense",
                    "type": "string",
                    "example": "Travel Expense",
                    "value": lambda o: o.category
                },
                "description": {
                    "description": "The description of the expense",
                    "type": "string",
                    "example": "Travel Expense for visit to Kenya",
                    "value": lambda o: o.category
                },
                "department": {
                    "description": "Department",
                    "type": "string",
                    "example": "Operations",
                    "value": lambda o: o.department
                },
                "receipt_picture": {
                    "description": "UUID of the Picture of the receipt",
                    "type": "string",
                    "example": "1111-2222-3333-4444",
                    "value": lambda o: o.receiptPicture
                },
                "receipt_type": {
                    "description": "Type of the receipt",
                    "type": "integer",
                    "example": "receipt",
                    "value": lambda o: o.receiptType
                },
                "account": {
                    "description": "ID of the accounting account",
                    "type": "integer",
                    "example": 1,
                    "deprecated": True,
                    "value": lambda o: o.account.id if o.account else None
                },
                "user_id": {
                    "description": "ID of the user having the expense",
                    "type": "integer",
                    "example": 1,
                    "value": lambda o: o.account.owner.webUserID if o.account else None
                },
                "reportedBy": {
                    "description": "ID of the User that created the expense",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.reportedBy.id if o.reportedBy else None,
                },
                "associatedTransfer": {
                    "description": "ID of the Transfer trelated to the expense",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.associatedTransfer.id if o.associatedTransfer else None,
                },
                "supporting_document_1": {
                    "description": "The first supporting document related to the expense",
                    "type": "string",
                    "example": "doc.jpeg",
                    "value": lambda o: o.supportingDoc1,
                },
                "supporting_document_1_type": {
                    "description": "The type of the first supporting document related to the expense",
                    "type": "integer",
                    "example": 1,
                    "value": lambda o: o.supportingDoc1Type,
                },
                "supporting_document_2": {
                    "description": "The second supporting document related to the expense",
                    "type": "string",
                    "example": "doc.jpeg",
                    "value": lambda o: o.supportingDoc2,
                },
                "supporting_document_2_type": {
                    "description": "The type of the second supporting document related to the expense",
                    "type": "integer",
                    "example": 1,
                    "value": lambda o: o.supportingDoc2Type,
                },
                "supporting_document_3": {
                    "description": "The third supporting document related to the expense",
                    "type": "string",
                    "example": "doc.jpeg",
                    "value": lambda o: o.supportingDoc3,
                },
                "supporting_document_3_type": {
                    "description": "The type of the third supporting document related to the expense",
                    "type": "integer",
                    "example": 1,
                    "value": lambda o: o.supportingDoc3Type,
                },
                "additional_data": {
                    "type": "object",
                    "properties": {
                        "litres_of_fuel": {
                            "type": "string",
                            "description": "The amount of fuel in litres if the category is fuel",
                            "example": "12.3",
                        },
                        "mileage": {
                            "description": "The mileage of the vehicle if the category is fuel",
                            "example": "123.4",
                            "type": "string",
                        },
                    },
                    "additionalProperties": False,
                    "value": lambda o: o.getAdditionalData(),
                },
            },
            'view_required': [],
            'create_required': ['date', 'amount', 'description', 'receipt_picture', 'category'],
            'create_allowed': [],
            'create_forbidden': ['id'],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': []
        }


    @staticmethod
    def sort(resultset, sorting_criteria, field_name="id", order="desc"):
        try:
            field_name, order = sorting_criteria.split(":")
        except ValueError as e:
            print("Error {}".format(e))

        field = Expense.id

        if field_name == "amount":
            field = Expense.amount

        if field_name == "date":
            field = Expense.date

        if field_name == "description":
            field = Expense.description

        if field_name == "id":
            field = Expense.id

        if field_name == "type":
            field = Expense.category

        if order == "desc":
            field = desc(field)

        return resultset.order_by(field)


class Transfer(accounting_db.Entity):
    entryDate = Required(datetime)
    requestDate = Required(datetime)
    madeDate = Optional(datetime)
    confirmDate = Optional(datetime)
    decisionDate = Optional(datetime)
    amount = Required(float)
    description = Optional(str)
    useDetails = Optional(str)
    status = Required(int)  # 0: Awaiting Decision, 1: Approved, -1: Denied
    decision = Optional(int)
    decisionNotes = Optional(str)
    fromAccount = Required(Account, reverse="transfersSent", column="fromaccount")
    toAccount = Required(Account, reverse="transfersReceived", column="toaccount")
    requestBy = Required(AccountingUser, reverse="transfersRequested", column="requestby")
    decisionBy = Optional(AccountingUser, reverse="transfersDecided", column="decisionby")
    madeBy = Optional(AccountingUser, reverse="transfersMade", column="madeby")
    usedForExpenses = Set(Expense, reverse='associatedTransfer')
    parentTransfer = Optional('Transfer', reverse='childTransfers', column="parenttransfer")
    childTransfers = Set('Transfer', reverse='parentTransfer')
    requestAccount = Optional('Account', column="requestaccount")
    approvedAccount = Optional('Account', column="approvedaccount")

    def getStatusName(self):
        return TransferStatus.getStatusName(self.status)

    def isAwaitingDecision(self):
        return (self.status == TransferStatus.awaitingDecision)

    def isApproved(self):
        return (self.status == TransferStatus.approved)

    def isMade(self):
        return (self.status == TransferStatus.made)

    @classmethod
    def made_by_account(cls, account):
        return cls.select(lambda t: (t.status == TransferStatus.made) and (t.fromAccount == account or t.toAccount == account))


class TransferStatus():
    approved = 1
    denied = -1
    awaitingDecision = 0
    made = 2

    def getStatusName(status):
        statusNames = {}
        statusNames[-1] = "Denied"
        statusNames[0] = "Awaiting Decision"
        statusNames[1] = "Approved"
        statusNames[2] = "Made"
        return statusNames[status]


class ExpenseReceiptTypes():
    unknown = 0
    receipt = 1
    petty_cash_voucher = 2
    contract = 3
    invoice = 4
    other = 10


def getExpenseReceiptTypeName(name_code):
    result = 'Unknown'
    names = {
        1: 'Receipt',
        2: 'Petty Cash Voucher',
        3: 'Contract',
        4: 'Invoice',
        10: 'Other',
    }

    if name_code in names.keys():
        result = names[name_code]

    return result
