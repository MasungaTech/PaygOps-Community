from worker_app.worker_app import worker_app
from datetime import datetime
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.services.contract_cache_service import ContractCacheService
from shared.helpers.chunk_executer import isolated_chunk_executer
from pony import orm
import config
from shared.logger.loggers import LogAPI


@worker_app.task(acks_late=False)
def check_cached_data_now():
    if config.DISABLE_HEAVY_TASKS:
        return 
    # We first update the critical data
    print('Checking contract cache accuracy...')
    check_contracts_in_list()
    print('Cache accuracy check completed')


def check_contracts_in_list():
    contracts_id = get_contracts_id()
    isolated_chunk_executer(contracts_id, Contract, check_contract, action_name='check cache coherence', chunk_size=100)


@orm.db_session
def get_contracts_id():
    today = datetime.now()
    day_of_week = today.weekday()
    return orm.select(c.id for c in Contract if c.id % 7 == day_of_week)[:]


@orm.db_session()
def check_contract(contract):
    ContractCacheService.check_cache_accuracy(contract, fix_if_needed=True)

