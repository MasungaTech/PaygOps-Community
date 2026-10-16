from constants import VIEW_GLOBAL_STOCK_PERMS, VIEW_STOCK_PERMS
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from stock_management_system.models import StockMovement, StockItem
from stock_management_system.services.stock_item_getter_service import StockItemGetterService
from stock_management_system.services.stock_movement_getter_service import StockMovementGetterService
from stock_management_system.services.stock_movement_creation_service import StockMovementCreationService


class AllStockItemsResource(BaseAPIResourceAll):

    LIST_SERVICE = StockItemGetterService
    LIST_PERMISSION = VIEW_STOCK_PERMS + VIEW_GLOBAL_STOCK_PERMS

    MODEL = StockItem
    TAG = 'Inventory'


class IndividualStockItemResource(BaseAPIResourceIndividual):

    GET_SERVICE = StockItemGetterService
    GET_GLOBAL_PERMISSION = VIEW_GLOBAL_STOCK_PERMS
    GET_PERMISSION = VIEW_STOCK_PERMS
    OBJECT_NAME = 'Stock Item'

    MODEL = StockItem
    TAG = 'Inventory'

    @classmethod
    def _get_relevant_entity(cls, item):
        if item.shop:
            return item.shop
        if item.user:
            return item.user.shop
    
    @classmethod
    def _get_relevant_person(cls, stock_item):
        if stock_item.client:
            return stock_item.client.person


class AllStockMovementsResource(BaseAPIResourceAll):
    ADD_SERVICE = StockMovementCreationService
    LIST_SERVICE = StockMovementGetterService
    LIST_PERMISSION = VIEW_STOCK_PERMS + VIEW_GLOBAL_STOCK_PERMS
    ALLOWED_API_CALLER = ['post']
    MODEL = StockMovement
    TAG = 'Inventory'


class IndividualStockMovementResource(BaseAPIResourceIndividual):
    GET_SERVICE = StockMovementGetterService
    GET_GLOBAL_PERMISSION = VIEW_GLOBAL_STOCK_PERMS
    GET_PERMISSION = VIEW_STOCK_PERMS
    EDIT_GLOBAL_PERMISSION = VIEW_GLOBAL_STOCK_PERMS
    EDIT_SERVICE = StockMovementGetterService
    OBJECT_NAME = 'Stock Movement'
    MODEL = StockMovement
    TAG = 'Inventory'
