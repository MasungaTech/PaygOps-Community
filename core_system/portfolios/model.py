from datetime import datetime
from decimal import Decimal

from pony import orm

from constants import OPTIONAL_MONEY_OPTIONS
from core_system.core_entities import db
from shared.api_helpers.model_definition_base import ModelDefinitionMixin


class PortfolioEntity(db.Entity, ModelDefinitionMixin):
    _table_ = 'portfolio'

    id = orm.PrimaryKey(int, auto=True)
    name = orm.Required(str)
    description = orm.Required(str)
    budget = orm.Optional(Decimal)
    contracts = orm.Set("Contract")
    associated_clients = orm.Set('Client', reverse='portfolio')
    associated_leads = orm.Set('Lead', reverse='portfolio')
    creation_datetime = orm.Required(str)

    modifiedDate = orm.Required(datetime, default=datetime.now, index=True, volatile=True)

    def before_update(self):
        self.modifiedDate = datetime.now()

    def get_link(self):
        from flask import url_for
        return url_for('portfolios.view_portfolio', portfolio_id=self.id)

    def get_display_id(self):
        return str(self.id)

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "This is the ID of the Portfolio."
                },
                'name': {
                    "description": "This is the name of the Portfolio.",
                    "type": "string",
                    "example": "Cookstove Project X",
                    "value": lambda o: o.name
                },
                'description': {
                    "description": "This is the description of the Portfolio.",
                    "type": "string",
                    "example": "Portfolio of clean cookstoves financed by X.",
                    "value": lambda o: o.description
                },
                'budget': {
                    "description": "This is the budget of the Portfolio.",
                    "oneOf": OPTIONAL_MONEY_OPTIONS,
                    "example": "100000.00",
                    "value": lambda o: None if o.budget is None else float(o.budget)
                },
            },
            "create_required": ['name', 'description'],
            "create_allowed": ['name', 'description', 'budget'],
            "edit_required": [],
            "edit_allowed": ['name', 'description', 'budget'],
            "view_required": [],
            "view_allowed": None
        }
