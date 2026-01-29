from core_system.portfolios.model import PortfolioEntity
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from core_system.portfolios.services.portfolio_service import PortfoliosService


class AllPortfoliosResource(BaseAPIResourceAll):

    LIST_SERVICE = PortfolioGetterService
    ADD_SERVICE = PortfoliosService
    LIST_PERMISSION = 'ViewPortfolios'
    ADD_PERMISSION = 'CreatePortfolios'
    MODEL = PortfolioEntity
    TAG = 'Portfolios'
    ALLOWED_API_CALLER = ["post"]