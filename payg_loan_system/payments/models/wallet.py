from datetime import datetime
from decimal import Decimal
from pony.orm import PrimaryKey, Required, Optional, \
    Set, select, desc, coalesce
from pony import orm
from core_system.core_entities import db
from shared.helpers.db_helpers import TypeClassBase
from config import WALLET_HUMAN_READABLE_TYPES
from shared.services.settings_service import SettingsService


class PaymentWalletType(TypeClassBase):
    cash = 'Cash'
    mobile_money = 'MPESA'
    agent_collection = 'MentorCash'
    old = '' # To be removed after migration


class PaymentWallet(db.Entity):
    _table_ = 'mpesa_account'
    id = PrimaryKey(int, auto=True)
    RegistrationDate = Required(datetime)
    FullName = Required(str)
    client = Optional("Client", column='entrepreneur')
    lead = Optional("Lead", column='lead')
    Payments = Set("Payment", cascade_delete=False)
    Type = Optional(str, index=True, py_check=PaymentWalletType.valid)
    user = Optional("User", column='user')
    # Mentor = Optional('Mentor') # TO DO: to be removed
    phone_number = Optional('PhoneNumbers', column="phone_number")
    account_phone_number = Optional(str)
    operator = Optional(str, index=True, py_check=lambda o: o is not None)

    payment_debits = Set('ReconciledPayment')
    owners = Set("PaymentWalletOwner")
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    # Cached properties
    cached_balance_positive = Optional(bool, default=False, index=True, volatile=True)

    orm.composite_key(FullName, operator)

    def get_link(self):
        from flask import url_for
        return url_for('payment.account', account_id=self.id)

    def get_display_id(self):
        return str(self.id)

    def check_data_coherence(self):
        if sum([bool(x) for x in [self.lead, self.client, self.user]])>1:
            raise Exception('WALLET_CAN_HAVE_JUST_ONE_OWNER')

    def before_insert(self):
        self.check_data_coherence()

    def before_update(self):
        self.check_data_coherence()

    def get_operator_label(self):
        return 'Mobile Money: {}' if self.operator else ('Mobile Money Wallet' if self.Type == PaymentWalletType.mobile_money else 'Cash Wallet')

    @property
    def composed_name(self):
        return self.FullName + coalesce(' ('+self.client.full_name+')', ' ('+self.lead.full_name+')', '')

    @property
    def owned(self):
        return bool(self.client) or bool(self.lead) or bool(self.user)

    @property
    def composed_name_display(self):
        if self.client:
            return self.FullName + ' ('+self.client.full_name+') '
        if self.lead:
            return self.FullName + ' ('+self.lead.full_name+') '
        if self.user:
            return self.FullName + ' ('+self.user.full_name+') [User]'
        return self.FullName

    def get_total_payments(self):
        return orm.sum(p.Amount for p in self.Payments) or Decimal(0)

    def get_total_reconciled(self):
        return orm.sum(reconciled.amount for reconciled in self.payment_debits) or Decimal(0)

    @property
    def balance(self):
        return select(p.Amount for p in self.Payments).sum()-select(
            r.amount for r in self.payment_debits
        ).sum()

    @property
    def has_negative_payments(self):
        return select(p for p in self.Payments if p.Amount < 0).exists()
    

    #deprecated: balance can be used in queries and improves performance
    def get_balance(self):
        total_payments = self.get_total_payments()
        total_reconciled = self.get_total_reconciled()
        balance = (total_payments - total_reconciled)
        return balance

    def get_last_payment(self):
        payments = select(payment for payment in db.Payment if payment.PaymentWallet == self)
        last_payment = payments.order_by(desc(db.Payment.PaymentReceptionTime)).first()
        return last_payment

    def get_reconciled_payments(self):
        return select(debit for debit in db.ReconciledPayment if debit.payment_account == self)

    @property
    def type_name(self):
        return WALLET_HUMAN_READABLE_TYPES.get(self.Type, WALLET_HUMAN_READABLE_TYPES[None])

    def payment_or_reconciled_changed(self):
        self.cached_balance_positive = True if self.balance > 0 else False

    @property
    def status(self):
        # Get the PaymentSendingGateways settings
        gateway_settings = SettingsService.get_setting('PaymentSendingGateways')
        
        # Convert wallet operator to lowercase for comparison
        wallet_operator = self.operator.lower() if self.operator else None
        
        if not wallet_operator:
            return "unavailable"
            
        # Check if the operator exists in settings
        if wallet_operator in gateway_settings:
            # Return status based on enabled flag
            return "active" if gateway_settings[wallet_operator]["enabled"] else "inactive"
            
        return "unavailable"


class PaymentWalletOwner(db.Entity):
    wallet = Required("PaymentWallet", column="wallet")
    client = Optional("Client", column='client')
    lead = Optional("Lead", column='lead')
    user = Optional("User", reverse="owned_wallets", column='user')
    approver = Optional("User", column='approver')
    date = Required(datetime)
    balance = Required(Decimal)

    def check_data_coherence(self):
        if self.lead and self.client:
            raise Exception('WALLET_CAN_HAVE_JUST_ONE_OWNER')

    def before_insert(self):
        self.check_data_coherence()

    def before_update(self):
        self.check_data_coherence()
