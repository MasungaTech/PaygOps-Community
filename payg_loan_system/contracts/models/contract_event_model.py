from core_system.core_entities import db
from datetime import datetime
from pony.orm import *
from decimal import Decimal
from shared.helpers.date_helper import getCurrentUtcDate, getDefaultDateStr
from shared.logger.loggers import Error
from shared.helpers.db_helpers import TypeClassBase
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.helpers.numbers import round_if_needed


class ContractEvent(db.Entity, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    contract = Required('Contract', column="contract")
    time = Required(datetime)
    type = Required(str)
    old_offer = Optional('Offer', reverse='offer_change_old_offer', column='old_offer')
    new_offer = Optional('Offer', reverse='offer_change_new_offer', column='new_offer')
    old_device = Optional('Device', reverse='contract_event_old_device', column='old_device')
    new_device = Optional('Device', reverse='contract_event_new_device', column="new_device")
    repayment = Optional('ContractRepayment', column="repayment")
    added_amount = Optional(Decimal)
    approver = Optional('User', column="approver")
    note = Optional(str)
    device_addon = Optional('ContractAddOn', column="device_addon", reverse="device_event")

    addons = Set('ContractAddOn')
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)

    def check_data_coherence(self):
        if self.added_amount and round(self.added_amount, 2) != self.added_amount:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')

    def get_narration(self):
        if self.type == ContractEventType.manual_discount:
            narration = f'Discount {round(self.repayment.amount_discounted, 2)}'
        elif self.type == ContractEventType.manual_delay:
            narration = f'Delay {round_if_needed((self.repayment.delay_given_in_hours if self.repayment and self.repayment.delay_given_in_hours else 0)/24, 2)} days'
        elif self.type == ContractEventType.repossession:
            narration = f'Old Device: {self.old_device.composed_serial}' if self.old_device else f'Old Device: -'
        elif self.type == ContractEventType.device_swap:
            if self.old_device and self.new_device:
                narration = f'Old Device: {self.old_device.composed_serial}, New Device: {self.new_device.composed_serial}'
            else:
                narration = ''
        elif self.type == ContractEventType.offer_change:
            narration = f'Old Offer: {self.old_offer.code}, New Offer: {self.new_offer.code}'
        elif self.type == ContractEventType.duration_change:
            addons_effect = ','.join([f'{a.reference} ({round(a.extension_days, 2)} days)' for a in self.sorted_addons()])
            narration = f'Add-ons and extensions: {addons_effect}'
        elif self.type == ContractEventType.expected_paid_change:
            narration = f'Adjusted amount: {self.added_amount}'
        elif self.type == ContractEventType.reference_pricing_change:
            addons_effect = ','.join([f'{a.reference} ({round(a.repayment_increase, 2)})' for a in self.sorted_addons()])
            narration = f'Add-ons and changes: {addons_effect}'
        elif self.type == ContractEventType.repayment_reversed:
            narration = f'Reversal ID: {self.repayment.id}, Repayment Reversed: {self.repayment.converse.id}'
        elif self.type == ContractEventType.value_change:
            addons_effect = ','.join([f'{a.reference} ({round(a.total_amount, 2)})' for a in self.sorted_addons()])
            narration = f'Add-ons and changes: {addons_effect}'
        elif self.type == ContractEventType.overpayment:
            narration = 'Contract overpaid'
        else:
            narration = ''
        return narration

    def before_insert(self):
        self.check_data_coherence()

    def before_update(self):
        self.check_data_coherence()
        self.modifiedDate = datetime.now()

    def sorted_addons(self):
        return sorted(self.addons, key=lambda a: a.id)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "description": "The ID of the event",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.id
                },
                'date': {
                    "description": "This is the date of the event ",
                    "oneOf": [
                        {
                            "type": "string",
                            "format": "date-time",
                        },
                        {
                            "type": "null",
                        }
                    ],
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.time
                },
                'type': {
                    "description": "The type of the repayment",
                    "type": "string",
                    "example": 'Creation',
                    "value": lambda o: o.type
                },
                'contract_reference': {
                    "description": "The reference of the contract the event is on",
                    "type": "integer",
                    "example": 4,
                    "value": lambda o: o.contract.reference
                },
                'client_id': {
                    "description": "The ID of the client owning the contract the event is on",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.contract.client.id
                },
                'repayment_id': {
                    "description": "The ID of the repayment associated with the event",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.repayment.id if o.repayment else None
                },
                'approver_user_id': {
                    "description": "The ID of the user that approved the event",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.approver.id if o.approver else None
                },
                'note': {
                    "description": "Note of the event",
                    "type": "string",
                    "example": "Discount for christmas",
                    "value": lambda o: o.note
                },
                'discounted_amount': {
                    "description": "The amount discounted by the event (for discounts)",
                    "type": "integer",
                    "example": 12.34,
                    "value": lambda o: o.repayment.amount_discounted if o.repayment else None
                },
                'old_device_serial': {
                    "description": "The serial number of the old device (for device change only)",
                    "type": "string",
                    "example": 'SOL-1234',
                    "value": lambda o: o.old_device.composed_serial if o.old_device else None
                },
                'new_device_serial': {
                    "description": "The serial number of the new device (for device change only)",
                    "type": "string",
                    "example": 'SOL-1234',
                    "value": lambda o: o.new_device.composed_serial if o.new_device else None
                },
                'old_offer_id': {
                    "description": "The ID of the old offer (for offer change only)",
                    "type": "integer",
                    "example": 6,
                    "value": lambda o: o.old_offer.id if o.old_offer else None
                },
                'new_offer_id': {
                    "description": "The ID of the new offer (for offer change only)",
                    "type": "integer",
                    "example": 6,
                    "value": lambda o: o.new_offer.id if o.new_offer else None
                }
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }


class ContractEventType(TypeClassBase):
    creation = 'Creation'
    offer_change = 'Offer Change'
    value_change = 'Value Change'
    reference_pricing_change = 'Reference Pricing Change'
    duration_change = 'Duration Change'
    device_swap = 'Device Swap'
    default = 'Default'
    completion = 'Completion'
    manual_delay = 'Manual Delay'
    manual_discount = 'Manual Discount'
    overpayment = 'Overpayment'
    repossession = 'Repossession'
    undo_default = 'Undo Default'
    undo_completion = 'Undo Completion'
    repayment_reversed = 'Repayment Reversal'
    expected_paid_change = 'Expected Paid Change'
    cancellation = 'Cancellation'
    pause = 'Pause'
    resume = 'Resume'
    downpayment_reversal = 'Downpayment Reversal'
    addon_device = 'Add-on Device'
    addon_device_removal = 'Add-on Device Removal'
    addon_device_swap = 'Add-on Device Swap'
    addon_device_assign = 'Add-on Device Assign'
