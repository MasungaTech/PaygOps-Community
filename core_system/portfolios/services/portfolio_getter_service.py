from shared.services.base_getter_service import BaseGetterService
from core_system.portfolios.model import PortfolioEntity


class PortfolioGetterService(BaseGetterService):

    OBJ_NAME = 'Portfolio'

    @classmethod
    def get_filtered_objects(cls, current_user=None, **kwargs):
        return PortfolioEntity.select()