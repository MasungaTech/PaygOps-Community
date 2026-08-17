from stock_management_system.services.product_sub_type_service import ProductSubTypeService
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual


class ProductModelIndividualResource(BaseAPIResourceIndividual):
    GET_SERVICE = ProductSubTypeService
    EDIT_SERVICE = ProductSubTypeService
    DELETE_SERVICE = ProductSubTypeService
    GET_PERMISSION = 'ConfigureProductAdmin'  
    EDIT_PERMISSION = 'ConfigureProductAdmin'      
    DELETE_PERMISSION = 'ConfigureProductAdmin'  
    MODEL = ProductSubType
    OBJECT_NAME = 'Product Sub-Type'
    TAG = 'Inventory'

class ProductModelAllResource(BaseAPIResourceAll):
    LIST_SERVICE = ProductSubTypeService
    ADD_SERVICE = ProductSubTypeService
    LIST_PERMISSION = 'ConfigureProductAdmin' 
    ADD_PERMISSION = 'ConfigureProductAdmin'       
    MODEL = ProductSubType
    TAG = 'Inventory'
