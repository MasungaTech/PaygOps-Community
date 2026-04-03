from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from core_system.portfolios.model import PortfolioEntity
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from core_system.portfolios.services.portfolio_service import PortfoliosService



class IndividualPortfolioResource(BaseAPIResourceIndividual):

    GET_SERVICE = PortfolioGetterService
    EDIT_SERVICE = PortfoliosService
    DELETE_SERVICE = PortfoliosService
    GET_PERMISSION = 'ViewPortfolios'
    GET_GLOBAL_PERMISSION = 'ViewPortfolios'
    EDIT_PERMISSION = 'EditPortfolios'
    EDIT_GLOABL_PERMISSION = 'EditPortfolios'
    DELETE_PERMISSION = 'DeletePortfolios'
    DELETE_GLOABL_PERMISSION = 'DeletePortfolios'
    OBJECT_NAME = 'Portfolio'
    MODEL = PortfolioEntity
    TAG = 'Portfolios'
    ALLOWED_API_CALLER = ["post", "delete"]
