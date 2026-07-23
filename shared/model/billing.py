from datetime import datetime
import random
from decimal import Decimal
from pony.orm import Required, Optional, Set, composite_key, Json
from constants import INTEGER_REQUIRED_OPTIONS, NUMBER_OF_BILLING_TIERS
from payg_loan_system.offers.models import OfferType
from core_system.core_entities import db
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.helpers.db_helpers import TypeClassBase



class BillingType(TypeClassBase):
    new = 'Microservices v202506'
    old = 'Premium v202406'
    new_premium = 'Premium v202508'

class Bill(db.Entity, ModelDefinitionMixin):

    date = Required(datetime, index=True)
    fxrate = Required(Decimal, scale=6)
    last_update = Required(datetime, default=datetime.now)

    billed_items = Set('BilledItem')
    aggregated_billed_items = Set('AggregatedBilledItem')
    number_of_active_contacts = Optional(int)
    bill_type = Optional(str, py_check=BillingType.valid, default=BillingType.old)
    enabled_features = Optional(Json)
    extra_billing_info = Optional(Json)

    def get_breakdown(self):
        # Always premium active-contract rules, independent of platform / bill_type.
        from enterprise_features.services.billing_service import BillingService

        return BillingService.get_active_contract_breakdown(
            self.date.month, self.date.year, self.fxrate
        )

    def get_aggregated_breakdown(self):
        # Always premium active-contract rules, independent of platform / bill_type.
        from enterprise_features.services.billing_service import BillingService

        return BillingService.get_active_contract_aggregated_breakdown(
            self.date.month, self.date.year, self.fxrate
        )

    @classmethod
    def get_model_definition(cls, op=None, **kwargs):
        base_definition = {
            'properties': {
                "date": {
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().replace(day=1, hour=0, minute=0, microsecond=0).isoformat(),
                    "description": "The date of the bill",
                    "value": lambda o: o.date
                },
                "last_update": {
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().replace(day=1, hour=0, minute=0, microsecond=0).isoformat(),
                    "description": "The date and time at which the bill information was last updated",
                    "value": lambda o: o.last_update
                },
                "fxrate": {
                    "type": "number",
                    "format": "float",
                    "example": 1.654321,
                    "description": "The exchange rate used to convert the billed items value to the base currency (USD)",
                    "value": lambda o: o.fxrate
                },
                "number_of_active_contacts": {
                    "type": "number",
                    "format": "integer",
                    "example": 1000,
                    "description": "The number of active contacts: persons that have active relationship with the company, this could be a lead with active sale process or an active client",
                    "value": lambda o: o.number_of_active_contacts
                },
                "bill_type": {
                    "type": "string",
                    "description": "The type of the bill",
                    "example": "New Billing",
                    "value": lambda o: o.bill_type
                },
                "breakdown": {
                    "type": "object",
                    "description": "The breakdown of the billed items by type and tier in form of json object",
                    "deprecated": True,
                    "properties": {
                        type_key: {
                            "type": "object",
                            "properties": {
                                f'TIER{tier}': {
                                    "type": "integer",
                                    "example": 1,
                                } for tier in range(0, NUMBER_OF_BILLING_TIERS)
                            }
                        } for type_key, type_value in OfferType.to_dict().items()
                    },
                    "example": {
                        type_key: {
                            f'TIER{tier}': random.randint(0, 2000) for tier in range(0, NUMBER_OF_BILLING_TIERS)
                        } for type_key, type_value in OfferType.to_dict().items()
                    },
                    "value": lambda o: o.get_breakdown()
                },
                "aggregated_breakdown": {
                    "type": "object",
                    "description": "The number of persons in each type and tier using aggregated contract's value for each person",
                    "properties": {
                        type_key: {
                            "type": "object",
                            "properties": {
                                f'TIER{tier}': {
                                    "type": "integer",
                                    "example": 1,
                                } for tier in range(0, NUMBER_OF_BILLING_TIERS)
                            }
                        } for type_key, type_value in OfferType.to_dict().items()
                    },
                    "example": {
                        type_key: {
                            f'TIER{tier}': random.randint(0, 2000) for tier in range(0, NUMBER_OF_BILLING_TIERS)
                        } for type_key, type_value in OfferType.to_dict().items()
                    },
                    "value": lambda o: o.get_aggregated_breakdown()
                }
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': [],
            'create_allowed': [],
            'create_required': []
        }

        # Dynamically include `enabled_features` only for New Billing
        base_definition['properties']["enabled_features"] = {
            "type": "object",
            "description": "The enabled features associated with this bill. Only present if bill_type is New Billing.",
            "example": {"feature_x": True, "feature_y": {"limit": 10}},
            "value": lambda o: o.enabled_features if o.bill_type == BillingType.new or o.bill_type == BillingType.new_premium else None
        }
        base_definition['properties']["extra_billing_info"] = {
            "type": "object",
            "description": "Additional billing information stored as JSON",
            "example": {"number_of_automation_executions": "value", "notes": "Additional notes"},
            "value": lambda o: o.extra_billing_info
        }
        return base_definition

class BilledItemType(TypeClassBase):
    loan = 'Loan'
    lump_sum = 'Lump Sum'
    time_based = 'Time Based'
    usage_based = 'Usage Based'
    contact = 'Contacts'


class BilledItem(db.Entity, ModelDefinitionMixin):

    bill = Required(Bill, column="bill", index=True)
    contract = Optional('Contract', column="contract")
    lead = Optional('Lead', column="lead")
    add_on = Optional('ContractAddOn', column="add_on")
    type = Required(str, py_check=BilledItemType.valid)
    value = Required(Decimal)
    tier = Required(int) #should not be used anymore
    status = Optional(str)
    last_interaction_date = Optional(datetime)
    start_date = Required(datetime)
    end_date = Optional(datetime)
    next_repayment_due_date = Optional(datetime)

    aggregated_billed_item = Optional('AggregatedBilledItem') #Should be required after migration

    @classmethod
    def get_model_definition(cls, op=None, **kwargs):
        return {
            'properties': {
                'value': {
                    'type': 'number',
                    'format': 'float',
                    'description': 'The value of the contract',
                    'example': 123.45,
                    'value': lambda o: o.value
                },
                'start_date': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'The start date of the contract',
                    'example': datetime.now().replace(day=1, hour=0, minute=0, microsecond=0).isoformat(),
                    'value': lambda o: o.start_date
                },
                'end_date': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'The end date of the offer',
                    'example': datetime.now().replace(day=1, hour=0, minute=0, microsecond=0).isoformat(),
                    'value': lambda o: o.end_date,
                },
                'next_repayment_due_date': {
                    'type': 'string',
                    'format': 'date-time',
                    'description': 'The next repayment due date of the contract',
                    'example': datetime.now().replace(day=1, hour=0, minute=0, microsecond=0).isoformat(),
                    'value': lambda o: o.next_repayment_due_date,
                },
                'contract_reference': {
                    'type': 'string',
                    'description': 'The contract to which this billed item belongs',
                    'value': lambda o: o.contract.reference if o.contract else None,
                    'example': 'C1234001',
                },
                'add_on_reference': {
                    'type': 'string',
                    'description': 'The add-on to which this billed item belongs',
                    'value': lambda o: o.add_on.reference if o.add_on else None
                },
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': [],
            'create_allowed': [],
            'create_required': []
        }


class AggregatedBilledItem(db.Entity, ModelDefinitionMixin):

    bill = Required(Bill, column="bill", index=True)
    person = Required('Person', column="person", index=True)
    type = Required(str, py_check=BilledItemType.valid)
    total_value = Required(Decimal)
    tier = Required(int)
    billed_items = Set('BilledItem')

    composite_key(bill, person, type)

    @classmethod
    def get_model_definition(cls, op=None, **kwargs):
        return {
            'properties': {
                'type': {
                    'type': 'string',
                    'description': 'The type of the offer',
                    'example': 'PAYG',
                    'value': lambda o: o.type
                },
                'total_value': {
                    'type': 'number',
                    'format': 'float',
                    'description': 'The total value of the offer',
                    'example': 123.45,
                    'value': lambda o: o.total_value
                },
                'tier': {
                    'type': 'integer',
                    'description': 'The tier of the offer',
                    'example': 1,
                    'value': lambda o: o.tier
                },
                'leads_id': {
                    "type": "array",
                    "description": "The ID of the Leads linked to the client",
                    "items": {
                        "oneOf": INTEGER_REQUIRED_OPTIONS,
                    },
                    "example": [123, 124],
                    "value": lambda o: [lead.id for lead in o.person.lead]
                },
                'client_id': {
                    "type": "integer",
                    "description": "The ID of the client",
                    "example": 123,
                    "value": lambda o: o.person.client.id if o.person.client else None
                },
                'billed_items': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': BilledItem.get_model_schema()['properties']
                    },
                    'example': [BilledItem.get_model_example()],
                    'description': 'The list of billed items',
                    'value': lambda o: [bi.get_serialized_object() for bi in o.billed_items]
                }
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': [],
            'create_allowed': [],
            'create_required': []
        }