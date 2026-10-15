from core_system.portfolios.model import PortfolioEntity
from decimal import Decimal
from shared.logger.loggers import Error
from shared.helpers.clock import Clock
from shared.services.base_service import BaseService


class PortfoliosService(BaseService):

    @classmethod
    def _edit_from_data_and_user(cls, portfolio, data_dict, user):
        portfolio.name = data_dict.get('name', portfolio.name)
        portfolio.description = data_dict.get('description', portfolio.description)
        budget = data_dict.get('budget', portfolio.budget)
        if budget is not None and budget != '':
            budget = Decimal(budget)
            if budget < 0:
                raise Error('The budget must be >0')
        else:
            budget = None
        portfolio.budget = budget
        return portfolio

    @classmethod
    def _add_from_data_and_user(cls, data_dict, user):
        budget = data_dict.get('budget')
        if budget is not None and budget != '':
            budget = Decimal(budget)
            if budget < 0:
                raise Error('The budget must be >0')
        else:
            budget = None
        this_portfolio = PortfolioEntity(
            name=data_dict['name'],
            description=data_dict['description'],
            budget=budget,
            creation_datetime=Clock.now(),
        )
        return this_portfolio

    @classmethod
    def _delete_from_object_and_user(cls, portfolio, user):
        if portfolio.contracts:
            raise Error('This portfolio has contracts and cannot be deleted.')
        if portfolio.associated_clients:
            raise Error('This portfolio has clients and cannot be deleted.')
        if portfolio.associated_leads:
            raise Error('This portfolio has leads and cannot be deleted.')
        portfolio.delete()
