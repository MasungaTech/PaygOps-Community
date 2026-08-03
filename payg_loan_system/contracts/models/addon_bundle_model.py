from werkzeug.exceptions import default_exceptions
from core_system.operational_entities.models import OperationalEntity
from payg_loan_system.contracts.models.addon_loan_extension_mode import AddOnLoanExtensionMode
from constants import MONEY_AMOUNT_PATTERN
from decimal import Decimal
from datetime import datetime
from pony.orm import PrimaryKey, Required, Optional, Set, select, coalesce, IntArray
from core_system.core_entities import db
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.logger.loggers import Error
from constants import INTEGER_PATTERN
from core_system.operational_entities.services.operational_entity_set_service import OperationalEntitySetService

def get_availability_config(items, available_field, entities_field):

    entities_allowed = None
    allowed = True
    for item in items:
        if ((available_field == 'available_for_sales' and not item.offer.version_for_sales) or
            (available_field == 'available_for_registration' and not item.offer.versions_for_registration.exists())):
            allowed = False
            entities_allowed = None
            break
        new_item_entities = getattr(item.offer, entities_field)
        if not entities_allowed:
            entities_allowed = new_item_entities
        else:
            if not item.offer.entities_allowed_for_leads:
                continue
            new_entities_allowed = OperationalEntitySetService.get_intersection_of_entities_sets(
                entities_allowed, new_item_entities
            )
            new_entities_allowed_ids = [oe.id for oe in new_entities_allowed]
            entities_allowed = OperationalEntity.select(lambda oe: oe.id in new_entities_allowed_ids)
        
    available = 0 if not allowed else 1 if entities_allowed else 2
    available_entities = [e.id for e in entities_allowed] if entities_allowed else []

    return available, available_entities


class ContractAddOnBundle(db.Entity, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    category = Optional('AddOnCategory', column="category")
    items = Set('ContractAddOnBundleItem')
    modifiedDate = Required(datetime, default=datetime.now, index=True, volatile=True)
    mobile_uuid = Optional(str, unique=True)
    deleted = Required(bool, default=False)

    # Cached attributes
    cached_available_for_leads = Optional(int) # 0: nowhere, 1: some entities, 2: everywhere
    cached_available_for_contracts = Optional(int) # 0: nowhere, 1: some entities, 2: everywhere
    cached_available_for_leads_entities = Optional(IntArray)
    cached_available_for_contracts_entities = Optional(IntArray)

    def update_cached_data(self):
            
        self.cached_available_for_leads, self.cached_available_for_leads_entities = get_availability_config(
            self.items, "available_for_sales", "entities_allowed_for_leads"
        )

        self.cached_available_for_contracts, self.cached_available_for_contracts_entities = get_availability_config(
            self.items, "available_for_registration", "entities_allowed_for_contracts"
        )
        

    @property
    def modified_date(self):
        return self.modifiedDate

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    def before_update(self):
        self.modifiedDate = datetime.now()

    @property
    def total_value(self):
        return sum([i.total_amount for i in self.items]) #needs to be done in python, too complex to do: select(i.total_amount for i in self.items).sum()

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "description": "The ID of the add-on bundle",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.id
                },
                'name': {
                    "description": "The name of the add-on bundle",
                    "type": "string",
                    "example": "Example Add-on Bundle",
                    "value": lambda o: o.name
                },
                'category': {
                    "description": "The name of the add-on bundle category",
                    "type": "string",
                    "example": "Category 1",
                    "value": lambda o: o.category.name if o.category else None
                },
                'items': {
                    "description": "List of items in that bundle (use `include_objects` param for include add-ons data)",
                    "type": "array",
                    "items": {
                        "oneOf": [{
                            "type": "integer"
                        }, {
                            "type": "object",
                            "properties": ContractAddOnBundleItem.get_model_schema()['properties']
                        }]
                    },
                    "example": [ContractAddOnBundleItem.get_model_example()],
                    "value": lambda o: [i.get_serialized_object() for i in o.items]
                }
            },
            "create_required": ['name'],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }


class ContractAddOnBundleItem(db.Entity, ModelDefinitionMixin):
    
    id = PrimaryKey(int, auto=True)
    bundle = Required('ContractAddOnBundle', column="bundle")
    offer = Required('AddOnOffer', column="offerwrapper")
    quantity_sold = Required(Decimal, default=1)
    loan_mode = Optional(str, py_check=AddOnLoanExtensionMode.ovalid)

    # To be removed after migration
    old_offer = Optional('AddOnOfferVersion', column="offer")


    @property
    def total_amount(self):
        return self.offer.version_for_bundle.price*self.quantity_sold

    @property
    def downpayment(self):
        return coalesce(self.offer.version_for_bundle.downpayment, 0)*self.quantity_sold

    @property
    def offer_version(self):
        return self.offer.version_for_bundle

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "description": "The ID of the add-on bundle item",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.id
                },
                'bundle_id': {
                    "description": "The ID of the add-on bundle the item is linked to",
                    "type": "integer",
                    "example": 4,
                    "value": lambda o: o.bundle.id
                },
                'offer_code': {
                    "oneOf": [{
                        "type": "string",
                    }, {
                        "type": "null"
                    }],
                    "description": "The code of the Add-on offer",
                    "example": "OFFER_1",
                    "value": lambda o: o.offer.code
                },
                'offer_id': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }, {
                        "type": "null"
                    }, { 
                        "type": "string", 
                        "maxLength": 0
                    }],
                    "description": "The Id of the Add-on offer",
                    "example": 12,
                    "value": lambda o: o.offer.id
                },
                'loan_mode': {
                    "oneOf": [{
                        "type": "string",
                    }, {
                        "type": "null"
                    }],
                    "description": "The type of loan extension",
                    "enum": AddOnLoanExtensionMode.to_list(),
                    "example": AddOnLoanExtensionMode.to_list()[0],
                    "value": lambda o: o.loan_mode,
                }, 
                'quantity_sold': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": MONEY_AMOUNT_PATTERN
                    }, {
                        "type": "number",
                        "format": "float"
                    }],
                    "description": "Amount sold of the Add-on",
                    "example": 12.20,
                    "value": lambda o: float(o.quantity_sold)
                }
            },
            "create_required": ['bundle_id', 'quantity_sold'],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }