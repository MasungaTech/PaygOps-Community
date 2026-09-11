from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from payg_loan_system.contracts.services.addon_bundle_list_service import AddonBundleListService
from shared.logger.loggers import Error
from payg_loan_system.contracts.models.addons_model import ContractAddOn
from constants import INTEGER_PATTERN
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.services.base_service import BaseService


class AddonsFromBundle(ModelDefinitionMixin, BaseService):
    
    NEEDS_RELOAD = False

    def __init__(self, user, bundle_id, lead_id, contract_reference):
        bundle = AddonBundleListService.get_from_user_and_id(user, bundle_id, strict=True)
        self.bundle = bundle
        if not lead_id and not contract_reference:
            raise Error('Either one of lead_id or contract_reference is required')
        lead = None
        if lead_id:
            lead = LeadGetterService.get_from_user_and_id(user, lead_id, strict=True)
        self.lead = lead
        contract = None
        if contract_reference:
            contract = ContractGetterService.get_from_user_and_properties(user, reference=contract_reference, strict=True)
        self.contract = contract

        self.addons = []
        for item in bundle.items:
            self.addons.append(AddonService.create(
                contract,
                item.offer.version_for_sales,
                item.quantity_sold,
                user,
                loan_mode=item.loan_mode,
                lead=lead,
                note='From bundle #'+str(+bundle.id)
            ))

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        return cls(user, data['bundle_id'], data.get('lead_id'), data.get('contract_reference'))

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            'properties': {
                "bundle_id": {
                    "oneOf": [{
                        "type": "string",
                        "pattern": INTEGER_PATTERN
                    }, {
                        "type": "integer"
                    }],
                    "example": 12,
                    "description": "The ID if the bundle from which add the add-ons",
                    "value": lambda o: o.bundle.id
                },
                "lead_id": {
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
                    "description": "The Id of the lead to which the Add-on was attached, only has a value if the add-on was sold in pre-sales stage. Use either this or contract_reference when creating.",
                    "example": 123,
                    "value": lambda o: o.lead.id if o.lead else None
                },
                'contract_reference': {
                    "type": "string",
                    "description": "The reference of contract of the Add-on. Use either this or lead_id when creating. ",
                    "example": "C100004",
                    "value": lambda o: o.contract.reference if o.contract else None
                },
                "add_ons": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": ContractAddOn.get_model_schema()['properties']
                    },
                    "example": [ContractAddOn.get_model_example()],
                    "description": "The list of add-ons created",
                    "value": lambda o: [a.get_serialized_object() for a in o.addons]
                }
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': [],
            'create_allowed': ["bundle_id", "lead_id", "contract_reference"],
            'create_required': ["bundle_id"]
        }
    
    @classmethod
    def get_affected_entity(cls, data, user, **kwargs):
        if 'lead_id' in data:
            lead = LeadGetterService.get_from_user_and_id(user, data['lead_id'], strict=True)
            return lead.person.village
        if "contract_reference" in data:
            contract = ContractGetterService.get_from_user_and_properties(user, reference=data['contract_reference'], strict=True)
            return contract.client.person.village


class AllAddonsFromBundleResource(BaseAPIResourceAll):

    ADD_SERVICE = AddonsFromBundle
    ADD_PERMISSION = 'AddAddOns'
    MODEL = AddonsFromBundle
    
    TAG = 'Add-On Bundles'