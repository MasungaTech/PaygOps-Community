from datetime import datetime, timedelta
from worker_app.worker_app import worker_app
from payg_loan_system.contracts.models.contract_model import Contract
from pony import orm
from shared.logger.loggers import LogAPI
import config

log_api = LogAPI()


@worker_app.task
def update_cached_data_now(volatile=False, force=False):
    if config.DISABLE_HEAVY_TASKS:
        return 
    # We first update the critical data
    print('Updating Cached Contract Data critical stats...')
    needing_update_list = get_contracts_id_needing_update()
    update_contracts_with_id(needing_update_list, force=force)
    # We then update all contracts volatile data if needed (only every 3 hours or so)
    if datetime.now().hour % 3 == 0 or volatile:
        print('Updating Cached Contract Data volatile stats...')
        all_active_list = get_all_recently_active_contracts_id()
        update_contracts_with_id(all_active_list, volatile=True)
    print('Cached Contract Data Updated')


def update_contracts_with_id(contracts_id, volatile=False, force=False):
    try:
        contract_count = len(contracts_id)
        current = 0
        print(f'Processing {contract_count} contracts...')
        for id in contracts_id:
            current += 1
            if current % 1000 == 0:
                print(f'Processed {current}/{contract_count}...')
            try:
                update_contract(id, volatile)
            except Exception as e:
                try:
                    update_contract(id, volatile, force)
                except Exception as e:
                    print(str(e))
                    log_api.FatalNoRequest(e)  
        print(f'Done processing {contract_count} contracts...')     
    except Exception as e:
        print(str(e))
        log_api.FatalNoRequest(e)


@orm.db_session
def get_contracts_id_needing_update():
    contracts_id = orm.select(c.id for c in Contract if c.contract_terms_cache_update_needed \
                                                     or c.contract_repayment_cache_update_needed \
                                                     or c.expected_paid_cache_update_needed)[:]
    return contracts_id


@orm.db_session
def get_all_recently_active_contracts_id():
    return orm.select(c.id for c in Contract if not c.end_time or c.end_time > (datetime.now()-timedelta(days=1)))[:]


@orm.db_session()
def update_contract(id, volatile=False, force=False):
    Contract.get(id=id).update_cached_data(volatile=volatile, force=force)
