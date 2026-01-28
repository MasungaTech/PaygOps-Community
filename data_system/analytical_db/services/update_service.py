from pony import orm

from data_system.analytical_db.models.addon_offers import AddOn_Offers
from data_system.analytical_db.models.addons import AddOns
from data_system.analytical_db.models.client_groups import Client_Groups
from data_system.analytical_db.models.clients import Clients
from data_system.analytical_db.models.contract_events import Contract_Events
from data_system.analytical_db.models.contract_offers import Contract_Offers
from data_system.analytical_db.models.contract_payments import \
    Contract_Payments
from data_system.analytical_db.models.contracts import Contracts
from data_system.analytical_db.models.device_metrics import Device_Metrics
from data_system.analytical_db.models.l0_entity_changes import \
    L0_Entity_Changes
import config

# Import enterprise models conditionally
from data_system.analytical_db.models.lead_generators import Lead_Generators
from data_system.analytical_db.models.leads import Leads
from data_system.analytical_db.models.leads_history import Leads_History
from data_system.analytical_db.models.operational_entity import \
    Operational_Entities
from data_system.analytical_db.models.payment_wallets import Payment_Wallets
from data_system.analytical_db.models.payments import Payments
from data_system.analytical_db.models.portfolios import Portfolios
# New DB
from data_system.analytical_db.models.question_answers import Question_Answers
from data_system.analytical_db.models.reconciled_payments import \
    Reconciled_Payments
from data_system.analytical_db.models.reversed_payments import \
    Reversed_Payments
from data_system.analytical_db.models.stock_items import (Product_SubTypes,
                                                          Stock_Items)
from data_system.analytical_db.models.stock_movements import Stock_Movements
from data_system.analytical_db.models.users import Users
from data_system.analytical_db.services.model_update_service import \
    ModelUpdateService
from data_system.analytical_db.models.quantity_stock_items import Quantity_Stock_Items
from data_system.analytical_db.models.quantity_stock_movements import Quantity_Stock_Movements
if config.ENABLE_ENTERPRISE_FEATURES:
    from data_system.analytical_db.models.interactions import Interactions
    from data_system.analytical_db.models.issues import Issues
    from data_system.analytical_db.models.task_type import Task_Types
    from data_system.analytical_db.models.task import Tasks


class AnalyticalDBUpdateService:

    # Build base models list (order matters here)
    _base_models = [
        Portfolios, Users, Client_Groups, Operational_Entities,
        Clients, Contract_Offers, Lead_Generators,
        Leads, Leads_History, L0_Entity_Changes, Contracts, AddOn_Offers, AddOns, Contract_Payments,
        Contract_Events, Question_Answers,Payment_Wallets, Payments, Reversed_Payments, Reconciled_Payments,
        Device_Metrics, 
        Product_SubTypes, Stock_Items, Stock_Movements, Quantity_Stock_Items, Quantity_Stock_Movements
    ]
    
    # Add enterprise models only if enterprise features are enabled
    if config.ENABLE_ENTERPRISE_FEATURES:
        MODELS = _base_models + [Issues, Interactions, Task_Types, Tasks]
    else:
        MODELS = _base_models

    # The models in this list will be processed a second time with reupdate=True after the rest
    # This allows to resolve issues with Foreign Key circular dependencies and ensure that they
    # are all fully updated
    REUPDATE = [Users, Operational_Entities]

    # The models in this list will be processed with force_update=True once a day
    # (to update ages or metrics that can move on a daily basis even if the object has not changed)
    if config.ENABLE_ENTERPRISE_FEATURES:
        FORCE_DAILY_UPDATE = [Clients, Leads, Issues]
    else:
        FORCE_DAILY_UPDATE = [Clients, Leads]

    @classmethod
    def update(cls, force_models=None, only_models=None, daily_update=False):
        if not force_models:
            force_models = [Contracts.__name__]
        print('Updating Analytical DB')
        highest_ids = cls._get_highest_id_for_models(cls.MODELS)
        models = only_models if only_models else cls.MODELS
        if daily_update:
            force_models = force_models + [
                m.__name__ for m in AnalyticalDBUpdateService.FORCE_DAILY_UPDATE]
        for model in models:
            force_update = (model.__name__ in force_models) if force_models else False
            cls._update_model(model, highest_ids[model.__name__], force_update=force_update)
        for model in cls.REUPDATE:
            cls._update_model(model, highest_ids[model.__name__], force_update=True, reupdate=True)

    @classmethod
    def _update_model(cls, model, highest_id, force_update=False, **kwargs):
        print(f'Getting objects to update for {model.__name__}...')
        to_delete_ids, to_insert_ids, to_update_ids = cls._get_ids_to_delete_insert_update(
            model, highest_id, force_update)
        ModelUpdateService.update_model_objects(
            model, to_delete_ids, to_insert_ids, to_update_ids, **kwargs)

    @classmethod
    @orm.db_session
    def _get_highest_id_for_models(cls, models):
        highest_ids = {}
        for model in models:
            ModelUpdateService.get_last_update(model)
            # We do that to make sure the metadata is always there
            highest_ids[model.__name__] = orm.max(obj.id for obj in model.base_model)
        return highest_ids

    @classmethod
    @orm.db_session
    def _get_ids_to_delete_insert_update(cls, model, highest_id, force_update=False):
        main_db_ids = set(cls._get_all_main_db_ids(model, highest_id).order_by(1)[:])
        analytical_db_ids = set(cls._get_all_analytical_db_ids(model).order_by(1)[:])
        to_delete_ids = list(analytical_db_ids - main_db_ids)
        to_insert_ids = list(main_db_ids - analytical_db_ids)
        del main_db_ids # This is critical as it can use a lot of RAM
        if force_update:
            to_update_ids = list(analytical_db_ids)
            del analytical_db_ids # This is critical as it can use a lot of RAM
        else:
            del analytical_db_ids # This is critical as it can use a lot of RAM
            updated_main_db_ids = set(cls._get_all_updated_ids(model, highest_id))
            failed_ids = cls._get_all_failed_ids(model).order_by(1)[:]
            failed_less_to_insert = set(failed_ids+to_insert_ids)
            to_update_ids = failed_ids + list(updated_main_db_ids-failed_less_to_insert)
        return to_delete_ids, to_insert_ids, to_update_ids

    @classmethod
    def _get_all_main_db_ids(cls, model, highest_id=None):
        if highest_id:
            return orm.select(o.id for o in model.base_model if o.id <= highest_id)
        else:
            return orm.select(o.id for o in model.base_model)

    @classmethod
    def _get_all_analytical_db_ids(cls, model):
        return orm.select(o.id for o in model)

    @classmethod
    def _get_all_failed_ids(cls, model):
        return orm.select(o.id for o in model if o.last_updated is None)

    @classmethod
    def _get_all_updated_ids(cls, model, highest_id=None):
        updated_on = ModelUpdateService.get_last_update(model)
        if highest_id:
            query = orm.select(
                (o.id, model.extended_modified_date(o))
                for o in model.base_model if (
                    o.id <= highest_id and model.extended_modified_date(o) > updated_on
                )
            )
        else:
            query = orm.select(
                (o.id, model.extended_modified_date(o))
                for o in model.base_model if model.extended_modified_date(o) > updated_on
            )
        # We paginate because it can be RAM heavy
        pagesize = 10000000
        left_to_process = True
        ids = []
        p = 1
        while left_to_process:
            results = query.order_by(2).page(p, pagesize=pagesize)[:]
            if results:
                ids += [o[0] for o in results]
                p+=1
            else:
                left_to_process = False
        return ids
