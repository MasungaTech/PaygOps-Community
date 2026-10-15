from datetime import datetime
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from shared.helpers.db_helpers import Optional, Required, PrimaryKey

from data_system.analytical_db.db import analytical_db


class Metadata(analytical_db.Entity, BaseAnalyticalDBModel):
    id = PrimaryKey(int, auto=True)
    table = Required(str, unique=True)
    updated_on = Optional(datetime)


from data_system.analytical_db.models.question_answers import Question_Answers
from data_system.analytical_db.models.clients import Clients
from data_system.analytical_db.models.contract_offers import Contract_Offers
from data_system.analytical_db.models.contracts import Contracts
from data_system.analytical_db.models.leads import Leads
import config

# Import enterprise models conditionally
if config.ENABLE_ENTERPRISE_FEATURES:
    from data_system.analytical_db.models.interactions import Interactions
    from data_system.analytical_db.models.issues import Issues
    from data_system.analytical_db.models.task_type import Task_Types
    from data_system.analytical_db.models.task import Tasks
from data_system.analytical_db.models.leads_history import Leads_History
from data_system.analytical_db.models.l0_entity_changes import L0_Entity_Changes
from data_system.analytical_db.models.lead_generators import Lead_Generators
from data_system.analytical_db.models.users import Users
from data_system.analytical_db.models.payments import Payments
from data_system.analytical_db.models.reconciled_payments import Reconciled_Payments
from data_system.analytical_db.models.contract_payments import Contract_Payments
from data_system.analytical_db.models.contract_events import Contract_Events
from data_system.analytical_db.models.client_groups import Client_Groups
from data_system.analytical_db.models.operational_entity import Operational_Entities
from data_system.analytical_db.models.portfolios import Portfolios
from data_system.analytical_db.models.contracts_history import Contracts_History
from data_system.analytical_db.models.addon_offers import AddOn_Offers
from data_system.analytical_db.models.addons import AddOns
from data_system.analytical_db.models.device_metrics import Device_Metrics
from data_system.analytical_db.models.stock_items import Stock_Items
from data_system.analytical_db.models.stock_movements import Stock_Movements
from data_system.analytical_db.models.payment_wallets import Payment_Wallets
from data_system.analytical_db.models.quantity_stock_items import Quantity_Stock_Items
from data_system.analytical_db.models.quantity_stock_movements import Quantity_Stock_Movements
