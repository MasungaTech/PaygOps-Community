from payg_loan_system.contracts.models.addons_model import AddOnType
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from core_system.core_entities import db
from datetime import datetime
from pony.orm import *
from decimal import Decimal
from shared.logger.loggers import Error, LogAPI


class ReconciledPayment(db.Entity, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    time = Required(datetime, index=True)
    amount = Required(Decimal, index=True) # IMPORTANT NOTE: The amount shown to user is inverted
    type = Required(str, py_check=ReconciledPaymentType.valid)
    note = Optional(str)
    payment_account = Required('PaymentWallet', column="payment_account")

    #destinations
    repayment = Optional('ContractRepayment', column="repayment")
    add_on = Optional('ContractAddOn', column="add_on")
    lead = Optional('Lead', column='lead', reverse='reconciled_payments')
    user = Optional('User', column="user")
    contract_pending_repayment = Optional('Contract', column='contract_pending_repayment')
    reversed_payment = Optional("ReversedPayment", column="reversed_payment")
    person = Optional('Person', column='person', reverse='reconciled_payments')

    linked_payment = Optional('Payment', column="linked_payment", reverse="reconciled_payments")
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    converse = Optional("ReconciledPayment", reverse="converse", column="converse")
    origin_reconciled_payment = Optional("ReconciledPayment", reverse="destination_reconciled_payment", column="origin_reconciled_payment", index=True)
    destination_reconciled_payment = Optional("ReconciledPayment", reverse="origin_reconciled_payment")

    # Cache
    # This updates only when the reconciled payment change 
    # or the Lead person changes (changing client)
    # it cannot change in other cases (user or contract can't change person)
    cached_person = Optional('Person', column="cached_person", volatile=True) 

    ADDON_TYPES = [ReconciledPaymentType.addon, ReconciledPaymentType.addon_payment_reversal]
    REPAYMENT_TYPES = [ReconciledPaymentType.repayment, ReconciledPaymentType.repayment_reversal]
    PENDING_TYPES = [ReconciledPaymentType.repayment_pending, ReconciledPaymentType.repayment_pending_reversal]
    USER_TYPES = [ReconciledPaymentType.user, ReconciledPaymentType.user_reversal]
    MANUALLY_REVERSABLE = [ReconciledPaymentType.addon, ReconciledPaymentType.repayment_pending, ReconciledPaymentType.user, ReconciledPaymentType.manual_adjustment, ReconciledPaymentType.blocked_during_lead_editing, ReconciledPaymentType.payment_pending_reconciliation]
    REVERSED_TYPES = [ReconciledPaymentType.addon_payment_reversal, ReconciledPaymentType.repayment_reversal, ReconciledPaymentType.downpayment_reversal, ReconciledPaymentType.repayment_pending_reversal, ReconciledPaymentType.payment_pending_reconciliation_reversal, ReconciledPaymentType.blocked_during_lead_editing_reversal, ReconciledPaymentType.user_reversal]

    def check_data_coherence(self):
        if round(self.amount, 2) != self.amount:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')
        assert not self.repayment or not self.contract_pending_repayment
        assert (self.type in [ReconciledPaymentType.manual_adjustment, ReconciledPaymentType.payment_reversal, ReconciledPaymentType.repayment, ReconciledPaymentType.repayment_reversal, ReconciledPaymentType.payment_to_client] or self.contract_pending_repayment or self.lead or self.add_on or self.user or self.reversed_payment or self.person or self.repayment), self.to_dict()
        if self.converse:
            assert self.amount == -self.converse.amount
            assert self.payment_account == self.converse.payment_account
            if self.repayment:
                assert self.repayment.converse == self.converse.repayment
            assert self.add_on == self.converse.add_on
            assert self.lead == self.converse.lead, f'Reconciliation Reversal mismatching: Original Lead: {self.lead}, Reversal Lead {self.converse.lead} for {self.to_dict()}'
            assert self.user == self.converse.user
            assert self.person == self.converse.person
            assert self.linked_payment == self.converse.linked_payment
            assert self.contract_pending_repayment == self.converse.contract_pending_repayment
        assert self.type not in self.ADDON_TYPES or self.add_on
        assert self.type not in self.PENDING_TYPES or self.contract_pending_repayment or self.lead
        assert self.type not in self.USER_TYPES or self.user
        assert self.type not in self.REVERSED_TYPES or self.converse, self.to_dict()
        assert self.amount >= 0 or self.type in self.REVERSED_TYPES + [
            ReconciledPaymentType.manual_adjustment,
            ReconciledPaymentType.payment_to_client,
            ReconciledPaymentType.addon,
            ReconciledPaymentType.payment_reversal
        ] or (
            self.linked_payment and
            self.linked_payment.Amount < 0
        ), f"Reconciliation of type {self.type} with negative amount {self.amount}"
        # The only addons that can be paid are lump sum or lead downpayment
        assert not self.add_on or self.add_on.offer_version.offer.type == AddOnType.lump_sum or self.add_on.lead

    def before_insert(self):
        balance = self.payment_account.get_balance()
        if balance < 0 and not self.payment_account.has_negative_payments:
            raise Exception(f'There is not sufficient balance ({balance}) to use that amount ({self.amount}). ')
        self.cached_person = self.get_person()
        self.check_data_coherence()

    def get_person(self):
        if self.repayment:
            return self.repayment.contract.client.person
        elif self.lead:
            return self.lead.person
        elif self.add_on and self.add_on.contract:
            return self.add_on.contract.client.person
        elif self.contract_pending_repayment:
            return self.contract_pending_repayment.client.person
        elif self.user:
            return self.user.person
        elif self.person:
            return self.person
        return None

    @property
    def can_be_manually_reversed(self):
        return self.type in self.MANUALLY_REVERSABLE

    def after_insert(self):
        if self.add_on and self.type != ReconciledPaymentType.addon_payment_reversal:
            self.add_on.time_paid = datetime.now()
        self.process_hooks()

    def before_update(self):
        try:
            self.cached_person = self.get_person()
        except Exception:
            # If get_person() fails, set to None and continuec
            self.cached_person = None
        self.check_data_coherence()
        self.modifiedDate = datetime.now()

    def after_update(self):
        self.process_hooks()

    def process_hooks(self):
        self.payment_account.payment_or_reconciled_changed()
        if self.linked_payment:
            self.linked_payment.payment_or_reconciled_changed()
        if self.add_on:
            self.add_on.update_cached_properties()
        if self.repayment:
            self.repayment.modifiedDate = datetime.now()
            self.repayment.contract.last_time_active = datetime.now()
        if self.lead:
            self.lead.modifiedDate = datetime.now()
            # Mark lead as active when payment is reconciled
            # This ensures inactive contacts become active when actions are performed on them
            self.lead.last_time_active = datetime.now()
        if self.user:
            self.user.modifiedDate = datetime.now()
        if self.contract_pending_repayment:
            self.contract_pending_repayment.modified_date = datetime.now()
        if self.person:
            self.person.modifiedDate = datetime.now()

        
    def get_related_entity(self):
        if self.repayment:
            return self.repayment.contract.client.person.get_entity()
        if self.lead:
            return self.lead.person.get_entity()
        if self.user:
            return self.user.shop
        if self.add_on:
            return self.add_on.contract.client.person.get_entity()
        if self.contract_pending_repayment:
            return self.contract_pending_repayment.client.person.get_entity()
        return None

    def get_destination_indicator(self, include_destination_details=False):
        if include_destination_details:
            base = {
                "repayment_id": self.repayment.id if self.repayment else None,
                "lead_id": self.lead.id if self.lead else None,
                "user_id": self.user.id if self.user else None,
                "client_id": self.person.client.id if self.person else None,
                "add_on_reference": self.add_on.reference if self.add_on else None,
                "contract_reference": self.repayment.contract.reference if self.repayment else None,
                "reversed": self.converse is not None,
            }
        else:
            base = {}
        if self.repayment:
            return {**base, **{
                'destination_type': 'contract_repayment',
                'destination': self.repayment.contract.reference,
            }}
        if self.contract_pending_repayment:
            return {**base, **{
                'destination_type': 'contract_repayment',
                'destination': self.contract_pending_repayment.reference
            }}
        if self.lead:
            return {**base, **{
                'destination_type': 'lead',
                'destination': self.lead.future_contract_reference
            }}
        if self.add_on:
            return {**base, **{
                'destination_type': 'add_on',
                'destination': self.add_on.contract.reference
            }}
        if self.user:
            return {**base, **{
                'destination_type': 'user',
                'destination': str(self.user.id)
            }}
        if self.person:
            return {**base, **{
                'destination_type': 'client',
                'destination': str(self.person.client.id)
            }}
        if self.linked_payment:
            LogAPI.Warning('Wrong reconciled payment destination indicator, set as adjustment but has a linked payment')
        return {**base, **{
            'destination_type': 'adjustment'
        }}

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            'properties': {
                "id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the reconciled payment",
                    "value": lambda o: o.id
                },
                "time": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2020-09-01T14:34:54",
                    "description": "The date and time at which the reconciled payment was created",
                    "value": lambda o: o.time
                },
                "amount": {
                    "type": "number",
                    "format": "float",
                    "example": "20.43",
                    "description": "The amount reconciled",
                    "value": lambda o: o.amount
                },
                "type": {
                    "type": "string",
                    "description": "The type of reconciliation",
                    "enum": ReconciledPaymentType.to_list(),
                    "value": lambda o: o.type
                },
                "note": {
                    "type": "string",
                    "example": "My note",
                    "description": "Any note attached when creating the reconciled payment",
                    "value": lambda o: o.note
                },
                "wallet": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the relevant wallet",
                    "value": lambda o: o.payment_account.id
                },
                "payment": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the payment from which the money was reconciled (if any)",
                    "value": lambda o: o.linked_payment.id if o.linked_payment else None
                },
                "payment_transaction_id": {
                    "type": "string",
                    "example": "TEST_REF_123456789",
                    "description": "The Transaction ID of the payment from which the money was reconciled (if any)",
                    "value": lambda o: o.linked_payment.Reference if o.linked_payment else None
                },
                "contract_reference": {
                    "type": "string",
                    "example": "C1202003",
                    "description": "The reference of the contract to which the money was reconciled (if any)",
                    "value": lambda o: o.repayment.contract.reference if o.repayment \
                             else o.contract_pending_repayment.reference if o.contract_pending_repayment \
                             else o.lead.future_contract_reference if o.lead \
                             else None
                },
                "lead": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the lead to which the money was reconciled to (if any)",
                    "value": lambda o: o.lead.id if o.lead else None
                },
                "user": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the user to which the money was reconciled to (if any)",
                    "value": lambda o: o.user.id if o.user else None
                },
                "client_id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the client to which the money was reconciled to (if any)",
                    "value": lambda o: o.person.client.id if o.person else None
                },
                "add_on": {
                    "type": "string",
                    "example": "C1202003-A3",
                    "description": "The reference of the add-on to which the money was reconciled to (if any)",
                    "value": lambda o: o.add_on.reference if o.add_on else None
                },
                "add_on_id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The reference of the add-on to which the money was reconciled to (if any)",
                    "value": lambda o: o.add_on.reference if o.add_on else None
                },
                "reversed_payment": {
                    "type": "string",
                    "example": 123,
                    "description": "The reference of the reverted payment (in case of payment reversal)",
                    "value": lambda o: o.reversed_payment.payment.Reference if o.reversed_payment else None
                },
                "reversed": {
                    "type": "boolean",
                    "example": False,
                    "description": "Wheather the reconciliation was reversed or not",
                    "value": lambda o: bool(o.converse)
                },
                "reversed_by": {
                    "type": "integer",
                    "example": 123,
                    "description": "The id of the reconciliation that reverses the current reconcile payment (if any)",
                    "value": lambda o: o.converse.id if o.converse else None
                },
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': [],
            'create_allowed': [],
            'create_required': [],
            'create_forbidden': [],
        }
