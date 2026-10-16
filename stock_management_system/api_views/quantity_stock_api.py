
from constants import VIEW_GLOBAL_STOCK_PERMS, VIEW_STOCK_PERMS
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from stock_management_system.quantity_stock_models import QuantityStockMovement
from stock_management_system.services.quantity_stock_movement_service import QuantityStockMovementService


class AllQuantityStockMovementsResource(BaseAPIResourceAll):
    ADD_SERVICE = QuantityStockMovementService
    LIST_SERVICE = QuantityStockMovementService
    LIST_PERMISSION = VIEW_STOCK_PERMS + VIEW_GLOBAL_STOCK_PERMS
    MODEL = QuantityStockMovement
    ALLOWED_API_CALLER = ['post']
    TAG = 'Inventory'


class IndividualQuantityStockMovementsResource(BaseAPIResourceIndividual):
    GET_SERVICE = QuantityStockMovementService
    GET_GLOBAL_PERMISSION = VIEW_GLOBAL_STOCK_PERMS
    GET_PERMISSION = VIEW_STOCK_PERMS
    EDIT_GLOBAL_PERMISSION = VIEW_GLOBAL_STOCK_PERMS
    EDIT_SERVICE = QuantityStockMovementService
    OBJECT_NAME = 'Quantity Stock Movement'
    MODEL = QuantityStockMovement
    TAG = 'Inventory'
    
