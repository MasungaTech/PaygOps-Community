from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from payg_loan_system.contracts.services.addon_bundle_service import AddonBundleService, AddonBundleItemService
from payg_loan_system.contracts.services.addon_bundle_list_service import AddonBundleListService, AddonBundleItemListService
from payg_loan_system.contracts.models.addon_bundle_model import ContractAddOnBundle, ContractAddOnBundleItem


class AllAddonBundleResource(BaseAPIResourceAll):
    LIST_SERVICE = AddonBundleListService
    ADD_SERVICE = AddonBundleService
    LIST_PERMISSION = 'ViewAddonOffers'
    ADD_PERMISSION = 'AddAddonOffers'
    MODEL = ContractAddOnBundle
    OBJECT_NAME = 'AddonBundle'
    TAG = 'Add-On Bundles'


class IndividualAddonBundleResource(BaseAPIResourceIndividual):
    GET_SERVICE = AddonBundleListService
    EDIT_SERVICE = AddonBundleService
    DELETE_SERVICE = AddonBundleService
    GET_PERMISSION = 'ViewAddonOffers'
    EDIT_PERMISSION = 'EditAddonOffers'
    DELETE_PERMISSION = 'EditAddonOffers'
    MODEL = ContractAddOnBundle
    OBJECT_NAME = 'AddonBundle'
    TAG = 'Add-On Bundles'


class AllAddonBundleItemResource(BaseAPIResourceAll):
    LIST_SERVICE = AddonBundleItemListService
    ADD_SERVICE = AddonBundleItemService
    LIST_PERMISSION = 'ViewAddonOffers'
    ADD_PERMISSION = 'AddAddonOffers'
    MODEL = ContractAddOnBundleItem
    OBJECT_NAME = 'AddonBundleItem'
    TAG = 'Add-On Bundles'


class IndividualAddonBundleItemResource(BaseAPIResourceIndividual):
    GET_SERVICE = AddonBundleItemListService
    EDIT_SERVICE = AddonBundleItemService
    DELETE_SERVICE = AddonBundleItemService
    GET_PERMISSION = 'ViewAddonOffers'
    EDIT_PERMISSION = 'EditAddonOffers'
    DELETE_PERMISSION = 'EditAddonOffers'
    MODEL = ContractAddOnBundleItem
    OBJECT_NAME = 'AddonBundleItem'
    TAG = 'Add-On Bundles'
