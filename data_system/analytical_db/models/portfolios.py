from pony.orm import Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from core_system.portfolios.model import PortfolioEntity
from datetime import datetime
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config
from decimal import Decimal


class Portfolios(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Portfolios are used to group contracts together, usually separating them by funding source'

    base_model = PortfolioEntity

    id = PrimaryKey(int, comment="The internal unique ID of the portfolio")
    name = Optional(str, comment="The name of the portfolio")
    description = Optional(str, comment="The description of the portfolio")
    budget = Optional(Decimal, comment="The budget of the portfolio")

    # Virtual (not stored in the database)
    leads = Set("Leads")
    contracts = Set("Contracts")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(portfolio):
        return {
            "id": portfolio.id,
            "name": portfolio.name,
            "description": portfolio.description,
            "budget": portfolio.budget,
            "last_updated": Portfolios.extended_modified_date(portfolio)
        }
