from payg_loan_system.contracts.services.addon_category_service import AddonCategoryService
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual


class AllAddonCategoriesResource(BaseAPIResourceAll):
    LIST_SERVICE = AddonCategoryService
    ADD_SERVICE = AddonCategoryService
    LIST_PERMISSION = 'ViewAddonOffers'
    ADD_PERMISSION = 'AddAddonOffers'
    MODEL = AddOnCategory
    TAG = "Add-On Offers"


class IndividualAddonCategoryResource(BaseAPIResourceIndividual):
    GET_SERVICE = AddonCategoryService
    EDIT_SERVICE = AddonCategoryService
    DELETE_SERVICE = AddonCategoryService
    GET_PERMISSION = 'ViewAddonOffers'
    EDIT_PERMISSION = 'EditAddonOffers'
    DELETE_PERMISSION = 'EditAddonOffers'
    OBJECT_NAME = 'Add On Category'
    MODEL = AddOnCategory
    TAG = 'Add-On Offers'
