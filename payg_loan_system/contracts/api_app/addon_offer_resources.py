from constants import FLOAT_OPTIONAL_OPTIONS, INTEGER_OPTIONAL_OPTIONS, MONEY_AMOUNT_PATTERN
from payg_loan_system.contracts.models.addon_loan_extension_mode import AddOnLoanExtensionMode
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from payg_loan_system.contracts.services.addons.addon_offer_version_getter_service import AddonOfferVersionGetterService
from payg_loan_system.contracts.services.addons.addon_offer_version_service import AddonOfferVersionService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from payg_loan_system.contracts.services.addons.addon_offer_service import AddonOfferService
from payg_loan_system.contracts.models.addons_model import AddOnOffer, AddOnOfferVersion, AddOnType
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.helpers.many_to_many_helpers import add_many_to_many_schema
from shared.services.base_service import BaseService



class OldAddOnOfferModelForAPI(ModelDefinitionMixin):

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        base_model = {
            "properties": {
                'id': {
                    "description": "The ID of the add-on offer version",
                    "type": "integer",
                    "example": 12,
                    "value": lambda o: o.id,
                    "comparable": False
                },
                'name': {
                    "description": "The name of the add-on offer",
                    "type": "string",
                    "example": "Example Add-on Offer",
                    "comparable": False,
                    "value": lambda o: o.offer.name
                },
                'code': {
                    "description": "The unique code of the add-on offer",
                    "type": "string",
                    "example": "EXAMPLE_CODE",
                    "comparable": False,
                    "value": lambda o: o.offer.code
                },
                'price': {
                    "description": "The unit price of the offer version",
                    "name": "Price",
                    "oneOf": [{
                        "type": "string",
                        "pattern": MONEY_AMOUNT_PATTERN
                    }, {
                        "type": "number",
                        "format": "float"
                    }],
                    "example": 12.34,
                    "value": lambda o: float(o.price),
                },
                'duration_change': {
                    "description": "The duration change per unit added to the loan (in days)",
                    "name": "Duration Change",
                    "oneOf": FLOAT_OPTIONAL_OPTIONS,
                    "example": 1,
                    "value": lambda o: float(o.duration_change),
                },
                'category': {
                    "description": "The name of the category of the add-on offer",
                    "name": "Category",
                    "type": "string",
                    "example": "Product",
                    "value": lambda o: o.offer.category.name if o.offer.category else None
                },
                'type': {
                    "description": "The type of the add-on offer",
                    "name": "Type",
                    "type": "string",
                    "enum": AddOnType.to_list(),
                    "value": lambda o: o.offer.type
                },
                'available': {
                    "description": "The availability status of the add-on offer version for registration, could be true (available) or false (unavailable).",
                    "name": "Available for registration",
                    "type": "boolean",
                    "example": False,
                    "value": lambda o: o.available_for_registration
                },
                'need_approval': {
                    "description": "The approval requirement of the add-on offer, could be true (need to be approved) or false (the add-ons will be automatically approved). Default value is not provided is false.",
                    "type": "boolean",
                    "name": "Approval Required",
                    "example": False,
                    "value": lambda o: o.offer.need_approval
                },
                'loan_mode': {
                    "name": "Loan Mode",
                    "type": "string",
                    "description": "The type of loan extension",
                    "enum": AddOnLoanExtensionMode.to_list()+ [""],
                    "value": lambda o: o.offer.loan_mode,
                },
                'downpayment': {
                    "oneOf": [{
                        "type": "string",
                        "pattern": MONEY_AMOUNT_PATTERN
                    }, {
                        "type": "number",
                        "format": "float"
                    }],
                    "name": "Downpayment",
                    "example": 6.34,
                    "description": "The amount to be paid as downpayment, if sold to leads",
                    "value": lambda o: o.downpayment,
                },
                'pre_sales': {
                    "type": "boolean",
                    "name": "Available for sales",
                    "description": "The availability status of the add-on offer version for new leads or contract offer changes, could be true (available) or false (unavailable).",
                    "example": True,
                    "value": lambda o: o.available_for_sales,
                },
                'enforce_extension_limit': {
                    "type": "boolean",
                    "name": "Enforce addon extension limit",
                    "description": "The enforce addon extension limit of the add-on offer  version for leads, could be true or false.",
                    "example": True,
                    "value": lambda o: o.enforce_extension_limit,
                },
                'based_on_id': {
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "description": "The ID of the Add-on offer in which this add-on offer is based on.",
                    "example": 12,
                    "comparable": False,
                    "value": lambda o: o.offer.based_on.id if o.offer.based_on else None,
                },
                'disable_base_offer_for_leads': {
                    "type": "boolean",
                    "description": "When creating an offer based on a previous one, this flag indicates whether the base offer should be disabled for sales.",
                    "default": False,
                    "example": True
                },
                'disable_base_offer_for_contracts': {
                    "type": "boolean",
                    "description": "When creating an offer based on a previous one, this flag indicates whether the base offer should be disabled for registration.",
                    "default": False,
                    "example": True
                },
                'replace_base_offer_in_bundles': {
                    "type": "boolean",
                    "description": "When creating an offer based on a previous one, this flag indicates whether the base offer should be replaced by the new one in add-on bundles.",
                    "default": True,
                    "example": True
                },
                'payment_mode': {
                    "description": "The type of the add-on offer, use `type` property instead.",
                    "name": "Payment mode",
                    "deprecated": True,
                    "type": "string",
                    "enum": AddOnType.to_list(),
                    "value": lambda o: o.offer.type
                },
                'allow_decimal_quantities': {
                    "type": "boolean",
                    "name": "Allow decimal quantities",
                    "description": "Allows decimal quantities of the add-on offer, could be true or false.",
                    "example": True,
                    "value": lambda o: o.offer.allow_decimal_quantities,
                },
                'purchasing_addon': {
                    "type": "boolean",
                    "name": "Purchasing addon",
                    "description": "Indicates whether the add-on offer is a purchasing add-on.",
                    "example": True,
                    "value": lambda o: o.offer.purchasing_addon,
                },
            },
            "create_required": ["code", "name", "type", "price"],
            "create_allowed": [],
            "create_forbidden": ["id"],
            "edit_required": [],
            "edit_allowed": [],
            "edit_forbidden": ["id"],
            "view_required": [],
            "view_allowed": [],
            "view_forbidden": ["disable_base_offer_for_leads", "disable_base_offer_for_contracts", "replace_base_offer_in_bundles"]
        }
        add_many_to_many_schema(
            base_model,
            "entities_allowed_for_leads",
            "the Operational Entities in which this add-on offer is available for sales",
            "Only leads in these entities can receive add-ons of this offer",
            value=lambda o: [c.id for c in o.offer.entities_allowed_for_leads]
        )
        add_many_to_many_schema(
            base_model,
            "entities_allowed_for_contracts",
            "the Operational Entities in which this add-on offer is available for registration",
            "Only leads in theses entities can get registered with add-ons of this offer and only contracts in this entities can receive add-ons of this offer",
            value=lambda o: [c.id for c in o.offer.entities_allowed_for_contracts]
        )
        return base_model

    @classmethod
    def get(cls, *args, **kwargs):
        return AddOnOfferVersion.get(*args, **kwargs)

class OldAllAddonOfferResource(BaseAPIResourceAll):
    LIST_SERVICE = AddonOfferVersionGetterService
    ADD_SERVICE = AddonOfferService
    LIST_PERMISSION = 'ViewAddonOffers'
    ADD_PERMISSION = 'AddAddonOffers'
    MODEL = OldAddOnOfferModelForAPI
    OBJECT_NAME = "Add-on Offer (Old)"
    TAG = "Add-On Offers"
    DEPRECATED = ["post", "get"]


class OldAddonOfferEditService(BaseService):

    @classmethod
    def _edit_from_data_and_user(cls, offer_version, data, user):
        AddonOfferVersionService.edit_from_data_and_user(offer_version, data, user)
        AddonOfferService.edit_from_data_and_user(offer_version.offer, data, user)
        return offer_version

class OldIndividualAddonOfferResource(BaseAPIResourceIndividual):
    GET_SERVICE = AddonOfferVersionGetterService
    EDIT_SERVICE = OldAddonOfferEditService
    GET_PERMISSION = 'ViewAddonOffers'
    EDIT_PERMISSION = 'EditAddonOffers'
    OBJECT_NAME = 'AddonOfferVersion'
    MODEL = OldAddOnOfferModelForAPI
    OBJECT_NAME = "Add-on Offer (Old)"
    TAG = 'Add-On Offers'
    DEPRECATED = ["post", "get"]


class AllAddonOfferResource(BaseAPIResourceAll):
    LIST_SERVICE = AddonOfferGetterService
    LIST_PERMISSION = 'ViewAddonOffers'
    ADD_SERVICE = AddonOfferService
    ADD_PERMISSION = 'AddAddonOffers'
    MODEL = AddOnOffer
    TAG = "Add-On Offers"
    ALLOWED_API_CALLER = ["post"]

class IndividualAddonOfferResource(BaseAPIResourceIndividual):
    GET_SERVICE = AddonOfferGetterService
    GET_PERMISSION = 'ViewAddonOffers'
    EDIT_SERVICE = AddonOfferService
    EDIT_PERMISSION = 'EditAddonOffers'
    DELETE_SERVICE = AddonOfferService
    DELETE_PERMISSION = 'EditAddonOffers'
    OBJECT_NAME = 'AddonOffer'
    MODEL = AddOnOffer
    TAG = 'Add-On Offers'


class AllAddonOfferVersionResource(BaseAPIResourceAll):
    LIST_SERVICE = AddonOfferVersionGetterService
    ADD_SERVICE = AddonOfferVersionService
    LIST_PERMISSION = 'ViewAddonOffers'
    ADD_PERMISSION = 'AddAddonOffers'
    MODEL = AddOnOfferVersion
    TAG = "Add-On Offers"


class IndividualAddonOfferVersionResource(BaseAPIResourceIndividual):
    GET_SERVICE = AddonOfferVersionGetterService
    EDIT_SERVICE = AddonOfferVersionService
    GET_PERMISSION = 'ViewAddonOffers'
    EDIT_PERMISSION = 'EditAddonOffers'
    OBJECT_NAME = 'AddonOfferVersion'
    MODEL = AddOnOfferVersion
    TAG = 'Add-On Offers'
